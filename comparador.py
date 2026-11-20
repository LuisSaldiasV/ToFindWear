"""Comparador de precios de ropa (Chile), filtrado por estilo baggy / boxy.

Uso:
    python comparador.py              # actualiza todo
    python comparador.py abajo        # solo pantalones/jorts/buzos
    python comparador.py arriba       # solo parte superior
    python comparador.py zapatillas   # solo zapatillas
    python comparador.py ver          # no busca, solo regenera la pagina
    python comparador.py colores      # no busca, mide colores de fotos nuevas y regenera
Genera resultados.html y guarda historial de precios en precios.db.
"""
import argparse, json, re, sqlite3, sys, threading, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import colores
import colores_foto

BASE = Path(__file__).parent
GRUPOS = ("abajo", "arriba", "zapatillas")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36",
      "Accept-Language": "es-CL,es;q=0.9"}


def log(msg):
    print(msg, flush=True)


# ---------- Red: consultas pausadas para no gatillar bloqueos ----------
ESPERA = {"shopify": 4.0, "default": 2.0}   # segundos minimos entre consultas
_ultima, _lock = {}, threading.Lock()
CONTEO = {}                                  # consultas hechas en esta corrida, por tipo
ESTADO_SHOPIFY = BASE / ".shopify_estado.json"


class Bloqueado(Exception):
    pass


def get(url, tipo="default"):
    host = urllib.parse.urlparse(url).netloc
    # Shopify limita por IP para todas sus tiendas juntas: la pausa se cuenta global, no por sitio
    clave = "shopify" if tipo == "shopify" else host
    headers = dict(UA, Accept="application/json") if tipo == "shopify" else UA
    for intento in range(3):
        with _lock:
            espera = _ultima.get(clave, 0) + ESPERA.get(tipo, 2.0) - time.time()
            _ultima[clave] = time.time() + max(espera, 0)
            CONTEO[tipo] = CONTEO.get(tipo, 0) + 1
        if espera > 0:
            time.sleep(espera)
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and intento < 2 and tipo != "shopify":   # Shopify: insistir alarga el bloqueo
                pausa = min(int(e.headers.get("Retry-After") or 30), 90)
                log(f"  … {host} pide esperar {pausa}s")
                time.sleep(pausa)
                continue
            if e.code in (429, 503):
                raise Bloqueado(host)
            raise
    raise Bloqueado(host)


def precio_int(txt):
    d = re.sub(r"\D", "", str(txt or ""))
    return int(d) if d else None


# ---------- Filtro de estilo ----------
def normalizar(cfg, titulo):
    t = titulo.lower()
    for frase in cfg.get("quitar_del_titulo", []):
        t = t.replace(frase, " ")
    return " " + re.sub(r"[^\w]+", " ", t) + " "


def _hay(texto, w):
    """Palabra completa; si tiene 5+ letras tambien vale como inicio de palabra (jogger -> joggers, ajustad -> ajustado)."""
    w = re.sub(r"[^\w]+", " ", w.lower()).strip()
    return (" " + w + " ") in texto or (len(w) >= 5 and (" " + w) in texto)


def cumple_estilo(cfg, grupo, titulo, estilo_propio=False, extra=""):
    """extra (ej. tags de Shopify) solo puede sumar para entrar, nunca excluye."""
    t = normalizar(cfg, titulo)
    pos = t + normalizar(cfg, extra) if extra else t
    regla = cfg["estilo"][grupo]
    nunca = regla["nunca"] + (cfg.get("tiendas_estilo_nunca", []) if estilo_propio else [])
    if any(_hay(t, w) for w in nunca):
        return False
    ns = regla.get("nunca_salvo")
    if ns and any(_hay(t, w) for w in ns["palabras"]) and not any(_hay(pos, w) for w in ns["salvo"]):
        return False
    if not any(_hay(pos, w) for w in regla["tipo"]):
        return False
    return estilo_propio or any(_hay(pos, w) for w in regla["debe_tener"])


def clasificar(cfg, titulo, estilo_propio, grupos, extra=""):
    """En que grupo cae un producto de una tienda que trae todo su catalogo."""
    for g in ("zapatillas", "abajo", "arriba"):
        if g in grupos and cumple_estilo(cfg, g, titulo, estilo_propio and g != "zapatillas", extra):
            return g
    return None


def genero(titulo, cat=""):
    if cat.startswith("J02"):
        return "hombre"
    if cat.startswith("J05"):
        return "mujer"
    if cat.startswith("J09"):
        return "niño"
    t = " " + re.sub(r"[^\w]+", " ", titulo.lower()) + " "
    if re.search(r" (niñ[oa]s?|kids?|infantil|junior|bebé|bebe) ", t):
        return "niño"
    if " unisex " in t:
        return "unisex"
    h = any(w in t for w in (" hombre ", " hombres ", " men ", " masculino "))
    m = any(w in t for w in (" mujer ", " mujeres ", " dama ", " women ", " wmns ", " femenino "))
    return "hombre" if h and not m else "mujer" if m and not h else "unisex" if h and m else "sin dato"


def marca_excluida(cfg, p):
    m = (p.get("marca") or "").lower().strip()
    return m in {x.lower() for x in cfg.get("marcas_excluidas", [])}


# ---------- Fuentes ----------
def falabella(cfg, grupos):
    fc = cfg.get("falabella", {})
    if not fc.get("activa", True):
        return []
    oficiales = {v.lower() for v in fc.get("vendedores_oficiales", ["falabella"])}
    out, vistos = [], set()
    for g in grupos:
        for q in cfg["busquedas"][g]:
            log(f"[Falabella] {q}")
            for pag in range(1, fc.get("paginas", 1) + 1):
                url = f"https://www.falabella.com/falabella-cl/search?Ntt={urllib.parse.quote_plus(q)}&page={pag}"
                try:
                    h = get(url)
                except Exception as e:
                    log(f"  ! Falabella '{q}': {e}")
                    if isinstance(e, Bloqueado):
                        return out
                    break
                m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
                if not m:
                    break
                res = json.loads(m.group(1)).get("props", {}).get("pageProps", {}).get("results", []) or []
                for x in res:
                    p = _falabella_item(x)
                    if not p or p["id"] in vistos or not cumple_estilo(cfg, g, p["titulo"]):
                        continue
                    vend, marca = p["vendedor"].lower().strip(), p["marca"].lower().strip()
                    oficial = vend in oficiales or (marca and (marca.replace(" ", "") in vend.replace(" ", "")
                                                               or vend.replace(" ", "") in marca.replace(" ", "")))
                    if not oficial:
                        continue
                    vistos.add(p["id"])
                    p["oficial"], p["grupo"], p["busqueda"] = True, g, q
                    out.append(p)
                if len(res) < 40:
                    break
    return out


def _falabella_item(x):
    precios = [(precio_int((pr.get("price") or [""])[0]), pr.get("crossed")) for pr in x.get("prices", [])]
    actuales = [v for v, c in precios if v and not c]
    tachados = [v for v, c in precios if v and c]
    if not actuales:
        return None
    tallas, colores, url_sel = [], [], x.get("url")
    for v in x.get("variants", []) or []:
        for o in v.get("options", []) or []:
            ts = [sz.get("value") for sz in o.get("sizes", []) or [] if sz.get("available")]
            tallas += [t for t in ts if t not in tallas]
            if v.get("type") == "COLOR":
                colores.append({"n": o.get("label"), "hex": "#" + (o.get("value") or "888"), "url": o.get("url"), "tallas": ts,
                                "img": f"https://media.falabella.com/falabellaCL/{o.get('mediaId')}_1/public"})
                if o.get("selected"):
                    url_sel = o.get("url")
    colores.sort(key=lambda c: c["url"] != url_sel)
    return {"fuente": "Falabella", "id": x.get("productId"), "titulo": x.get("displayName", ""),
            "marca": x.get("brand", ""), "vendedor": x.get("sellerName", ""), "cat": x.get("merchantCategoryId") or "",
            "precio": min(actuales), "precio_antes": max(tachados) if tachados else None,
            "rating": float(x["rating"]) if x.get("rating") else None,
            "reviews": int(x["totalReviews"]) if str(x.get("totalReviews", "")).isdigit() else 0,
            "url": url_sel, "img": (x.get("mediaUrls") or [None])[0], "tallas": tallas, "colores": colores}


def _ld_productos(h):
    """Productos desde los datos estructurados (JSON-LD) de una pagina de resultados."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("@type") == "Product":
                out.append(o)
            else:
                for v in o.values():
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', h, re.S):
        if '"Product"' in m.group(1):
            try:
                walk(json.loads(m.group(1)))
            except ValueError:
                pass
    return out


def paris_ripley(cfg, grupos, tienda):
    pr = cfg.get("paris_ripley", {})
    marcas = [m.lower() for m in pr.get(tienda, [])]
    url_busq = {"paris": "https://www.paris.cl/search/?q={}", "ripley": "https://simple.ripley.cl/search/{}"}[tienda]
    nombre = tienda.capitalize()
    out, vistos = [], set()
    for marca in marcas:
        for term in pr.get("terminos", []):
            q = f"{marca} {term}"
            log(f"[{nombre}] {q}")
            try:
                h = get(url_busq.format(urllib.parse.quote(q)))
            except Exception as e:
                log(f"  ! {nombre} '{q}': {e}")
                if isinstance(e, Bloqueado):
                    return out
                continue
            for x in _ld_productos(h):
                bm = ((x.get("brand") or {}).get("name") or "").lower()
                if bm.replace("´", "'") != marca.replace("´", "'"):
                    continue
                of = x.get("offers") or {}
                if isinstance(of, list):
                    of = of[0] if of else {}
                precio = precio_int(of.get("price"))
                if not precio or "OutOfStock" in str(of.get("availability", "")):
                    continue
                lista = [precio_int(s.get("price")) for s in of.get("priceSpecification", []) or []
                         if "ListPrice" in str(s.get("priceType", ""))]
                antes = max([v for v in lista if v] or [0]) or None
                url = x.get("url") or of.get("url")
                pid = str(x.get("sku") or url.rstrip("/").split("/")[-1])
                titulo = x.get("name", "")
                g = clasificar(cfg, titulo, False, grupos)
                if not g or pid in vistos:
                    continue
                vistos.add(pid)
                img = x.get("image")
                out.append({"fuente": nombre, "id": pid, "titulo": titulo.title() if titulo.isupper() else titulo,
                            "marca": (x.get("brand") or {}).get("name", ""), "vendedor": nombre, "oficial": True,
                            "precio": precio, "precio_antes": antes if antes and antes > precio else None,
                            "rating": None, "reviews": 0, "url": url, "img": img[0] if isinstance(img, list) else img,
                            "tallas": [], "colores": [], "cat": "", "grupo": g, "busqueda": q})
    return out


def shopify_en_enfriamiento():
    """Tras un bloqueo, no se consulta Shopify hasta el dia siguiente."""
    try:
        hasta = json.loads(ESTADO_SHOPIFY.read_text(encoding="utf-8")).get("bloqueado_hasta", "")
    except (OSError, ValueError):
        return False
    return date.today().isoformat() < hasta


def a_int(valor):
    """Precio de Shopify ('24990.00') a entero; None si no es valido."""
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return None


MAX_PAGINAS = 20


def shopify(cfg, grupos):
    out = []
    if shopify_en_enfriamiento():
        log("[Shopify] en enfriamiento por bloqueo previo: hoy no se consulta (se mantienen sus datos anteriores)")
        return out
    for dominio, opc in cfg.get("tiendas_shopify", {}).items():
        if dominio.startswith("_"):
            continue
        log(f"[Shopify] {dominio}")
        prods = []
        try:
            for pag in range(1, MAX_PAGINAS + 1):
                lote = json.loads(get(f"https://{dominio}/products.json?limit=250&page={pag}", "shopify")).get("products")
                if not isinstance(lote, list):
                    raise ValueError("respuesta inesperada (no trae lista de productos)")
                prods += lote
                if len(lote) < 250:
                    break
            else:
                log(f"  ! {dominio}: se alcanzo el maximo de {MAX_PAGINAS} paginas, el catalogo puede estar incompleto")
        except Bloqueado:
            manana = (date.today() + timedelta(days=1)).isoformat()
            ESTADO_SHOPIFY.write_text(json.dumps({"bloqueado_hasta": manana, "tienda": dominio}), encoding="utf-8")
            log(f"  ! Shopify pidio pausa en {dominio}: no se consulta hasta {manana} (se mantienen sus datos anteriores)")
            break
        except Exception as e:
            log(f"  ! {dominio}: {e} (se mantienen sus datos anteriores)")
            continue
        fuente = dominio.removeprefix("www.")
        n, vistos = 0, set()
        for x in prods:
            if x.get("handle") in vistos:
                continue
            vistos.add(x.get("handle"))
            tags = x.get("tags") or []
            tags = " ".join(tags) if isinstance(tags, list) else str(tags)
            g = clasificar(cfg, x.get("title", "") + " " + (x.get("product_type") or ""), opc.get("estilo_propio"), grupos, extra=tags)
            if not g:
                continue
            vs = [v for v in x.get("variants", []) if v.get("available", True) and a_int(v.get("price"))]
            if not vs:
                continue
            precio = min(a_int(v["price"]) for v in vs)
            antes = max((a_int(v.get("compare_at_price")) or 0 for v in vs), default=0) or None
            opciones = [o.get("name", "").lower() for o in x.get("options", [])]
            idx = next((i for i, o in enumerate(opciones) if any(k in o for k in ("talla", "size", "tamaño", "numero", "número"))), None)
            tallas = []
            for v in vs if idx is not None else []:   # sin opcion de talla: mejor vacio que guardar colores
                t = v.get(f"option{idx + 1}") or ""
                if t and t.lower() != "default title" and t not in tallas:
                    tallas.append(t)
            # variantes de color (mismo formato que Falabella: nombre, hex, url, foto y tallas de ese color)
            icol = next((i for i, o in enumerate(opciones) if any(k in o for k in ("color", "colour", "tono"))), None)
            cols = {}
            for v in vs if icol is not None else []:
                nombre = v.get(f"option{icol + 1}") or ""
                if not nombre:
                    continue
                c = cols.setdefault(nombre, {"n": nombre, "hex": (colores.buscar(nombre) or {}).get("hex", "#888888"),
                                             "url": f"https://{dominio}/products/{x['handle']}?variant={v.get('id')}",
                                             "img": (v.get("featured_image") or {}).get("src") or (x.get("images") or [{}])[0].get("src"),
                                             "tallas": []})
                t = v.get(f"option{idx + 1}") if idx is not None else None
                if t and t not in c["tallas"]:
                    c["tallas"].append(t)
            out.append({"fuente": fuente, "id": x["handle"], "titulo": x.get("title", ""),
                        "marca": x.get("vendor", "") or fuente, "vendedor": fuente, "oficial": True,
                        "precio": precio, "precio_antes": antes if antes and antes > precio else None,
                        "rating": None, "reviews": 0, "url": f"https://{dominio}/products/{x['handle']}",
                        "img": (x.get("images") or [{}])[0].get("src"), "tallas": tallas, "colores": list(cols.values()), "cat": "",
                        "grupo": g, "busqueda": "catalogo", "unisex": opc.get("estilo_propio")})
            n += 1
        log(f"  {dominio}: {len(prods)} en catalogo, {n} de tu estilo")
    return out


# ---------- Confianza ----------
def confianza(p):
    """Puntaje 0-100: tienda oficial, rating y cantidad de reseñas."""
    s = 40 if p.get("oficial") else 15
    if p.get("rating"):
        s += max(0, (p["rating"] - 3) / 2) * 35
    s += min(p.get("reviews") or 0, 200) / 200 * 25
    return round(s)


# ---------- Base de datos ----------
def db():
    c = sqlite3.connect(BASE / "precios.db")
    c.execute("""CREATE TABLE IF NOT EXISTS precios(
        fuente TEXT, id TEXT, fecha TEXT, precio INTEGER, titulo TEXT,
        PRIMARY KEY(fuente, id, fecha))""")
    c.execute("""CREATE TABLE IF NOT EXISTS productos(
        fuente TEXT, id TEXT, grupo TEXT, busqueda TEXT, titulo TEXT, marca TEXT,
        vendedor TEXT, precio INTEGER, precio_antes INTEGER, rating REAL, reviews INTEGER,
        url TEXT, img TEXT, confianza INTEGER, primera_vez TEXT, ultima_vez TEXT,
        PRIMARY KEY(fuente, id))""")
    cols = [r[1] for r in c.execute("PRAGMA table_info(productos)")]
    for col in ("tallas", "genero", "colores"):
        if col not in cols:
            c.execute(f"ALTER TABLE productos ADD COLUMN {col} TEXT")
    c.execute("""CREATE TABLE IF NOT EXISTS color_foto(
        img TEXT PRIMARY KEY, n TEXT, hex TEXT, neutro INTEGER, url_ok TEXT, fecha TEXT)""")
    return c


def guardar(c, p):
    hoy = date.today().isoformat()
    ult = c.execute("SELECT precio FROM precios WHERE fuente=? AND id=? ORDER BY fecha DESC LIMIT 1",
                    (p["fuente"], p["id"])).fetchone()
    if not ult or ult[0] != p["precio"]:   # solo se guarda cuando el precio cambia
        c.execute("INSERT OR REPLACE INTO precios VALUES(?,?,?,?,?)", (p["fuente"], p["id"], hoy, p["precio"], p["titulo"]))
    gen = "unisex" if p.get("unisex") else genero(p["titulo"], p.get("cat", ""))
    c.execute("""INSERT INTO productos(fuente,id,grupo,busqueda,titulo,marca,vendedor,precio,precio_antes,rating,reviews,
        url,img,confianza,primera_vez,ultima_vez,tallas,genero,colores) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(fuente,id) DO UPDATE SET grupo=excluded.grupo, titulo=excluded.titulo, marca=excluded.marca,
        vendedor=excluded.vendedor, precio=excluded.precio, precio_antes=excluded.precio_antes, rating=excluded.rating,
        reviews=excluded.reviews, url=excluded.url, img=excluded.img, confianza=excluded.confianza,
        ultima_vez=excluded.ultima_vez, tallas=excluded.tallas, genero=excluded.genero, colores=excluded.colores""",
        (p["fuente"], p["id"], p["grupo"], p["busqueda"], p["titulo"], p["marca"], p["vendedor"], p["precio"],
         p["precio_antes"], p["rating"], p["reviews"], p["url"], p["img"], confianza(p), hoy, hoy,
         json.dumps(p.get("tallas", []), ensure_ascii=False), gen, json.dumps(p.get("colores", []), ensure_ascii=False)))


def podar(c, cfg):
    """Borra lo que no aparece hace tiempo (agotado o retirado) para no acumular basura."""
    limite = (date.today() - timedelta(days=cfg.get("dias_sin_ver_para_borrar", 30))).isoformat()
    viejos = c.execute("SELECT fuente,id FROM productos WHERE ultima_vez < ?", (limite,)).fetchall()
    for f, i in viejos:
        c.execute("DELETE FROM productos WHERE fuente=? AND id=?", (f, i))
        c.execute("DELETE FROM precios WHERE fuente=? AND id=?", (f, i))
    c.commit()
    if viejos:
        log(f"Borrados {len(viejos)} productos que no aparecen hace mas de {cfg.get('dias_sin_ver_para_borrar', 30)} dias.")


def fotos_a_revisar(c):
    """(img, grupo) de productos vigentes cuyo color aun no se ha medido en la foto."""
    hechas = {r[0] for r in c.execute("SELECT img FROM color_foto")}
    desde = (date.today() - timedelta(days=4)).isoformat()
    pend = {}
    for img, grupo, cols in c.execute("SELECT img, grupo, colores FROM productos WHERE ultima_vez >= ?", (desde,)):
        vs = [v.get("img") for v in json.loads(cols or "[]") if v.get("img")]
        for u in vs or [img]:
            if u and u not in hechas:
                pend[u] = grupo
    return list(pend.items())


def colorear_fotos(c):
    """Mide el color de cada foto nueva y lo guarda (cada foto se analiza una sola vez)."""
    if not colores_foto.disponible():
        log("Colores por foto: falta Pillow (pip install pillow), se usan solo los nombres de las tiendas.")
        return
    pend = fotos_a_revisar(c)
    if not pend:
        return
    log(f"Colores por foto: analizando {len(pend)} imagenes nuevas...")
    hoy = date.today().isoformat()
    with ThreadPoolExecutor(4) as ex:   # imagenes de CDN: pocas a la vez para no molestar
        res = list(ex.map(lambda x: (x[0], colores_foto.color_de_foto(*x)), pend))
    ok = 0
    for img, r in res:
        if r:
            ok += 1
            c.execute("INSERT OR REPLACE INTO color_foto VALUES(?,?,?,?,?,?)", (img, r["n"], r["hex"], int(r["neutro"]), r["url"], hoy))
    c.commit()
    log(f"Colores por foto: {ok} de {len(pend)} leidas (las fallidas se reintentan en la proxima corrida).")


def es_mi_talla(cfg, p):
    """True/False si la prenda trae tallas y alguna es tuya; None si la tienda no informa tallas."""
    mias = {t.upper() for t in cfg.get("mis_tallas", {}).get(p["grupo"], [])}
    if not mias or not p["tallas"]:
        return None
    # "44", "T-44", "44 (34)", "L/XL" -> se compara cada pedazo; "34-30" es cintura-largo: solo cuenta la cintura
    def pedazos(t):
        t = str(t).upper().strip()
        m = re.fullmatch(r"(\d{2})\s*[-/X]\s*(\d{2})", t)
        return [m.group(1)] if m else [x for x in re.split(r"[^0-9A-Z]+", t) if x]
    return any(x in mias for t in p["tallas"] for x in pedazos(t))


def cargar_todo(c, cfg):
    """Lee la base, aplica el filtro de estilo actual (sin borrar nada) y calcula el puntaje de oferta."""
    c.row_factory = sqlite3.Row
    hist = {}
    for r in c.execute("SELECT fuente,id,fecha,precio FROM precios ORDER BY fecha"):
        hist.setdefault((r["fuente"], r["id"]), []).append([r["fecha"], r["precio"]])
    propias = {d.removeprefix("www."): o.get("estilo_propio") for d, o in cfg.get("tiendas_shopify", {}).items() if not d.startswith("_")}
    # ultima lectura exitosa de cada tienda: si una tienda estuvo bloqueada, sus productos no caducan
    ultima_lectura = {f: u for f, u in c.execute("SELECT fuente, MAX(ultima_vez) FROM productos GROUP BY fuente")}
    foto = {r["img"]: {"n": r["n"], "hex": r["hex"], "neutro": bool(r["neutro"]), "url": r["url_ok"]}
            for r in c.execute("SELECT * FROM color_foto")}
    out = []
    for r in c.execute("SELECT * FROM productos"):
        p = dict(r)
        if not cumple_estilo(cfg, p["grupo"], p["titulo"], bool(propias.get(p["fuente"])) and p["grupo"] != "zapatillas") \
                or marca_excluida(cfg, p) or "niño" in (p["genero"], genero(p["titulo"])):
            continue
        p["tallas"] = json.loads(p["tallas"] or "[]")
        p["colores"] = json.loads(p["colores"] or "[]")
        p["color"] = colores.detectar(p, foto)
        for v in p["colores"]:                     # foto que si carga (Falabella a veces usa _01 y no _1)
            if v.get("img") in foto:
                v["img"] = foto[v["img"]]["url"]
        if p["img"] in foto:
            p["img"] = foto[p["img"]]["url"]
        for c_ in p["color"]:                      # circulos de las tarjetas con el tono realista
            if c_["k"] is not None:
                p["colores"][c_["k"]]["hex"] = c_["hex"]
        h = hist.get((p["fuente"], p["id"]), [])
        previos = [x[1] for x in h[:-1]]
        p["hist"] = h
        p["min_hist"] = min(x[1] for x in h) if h else p["precio"]
        if not previos:
            p["estado"] = "nuevo"
        elif p["precio"] <= min(previos) and p["precio"] < max(previos):
            p["estado"] = "minimo"
        elif p["precio"] < sum(previos) / len(previos) * 0.9:
            p["estado"] = "bajo"
        elif p["precio"] > sum(previos) / len(previos) * 1.05:
            p["estado"] = "subio"
        else:
            p["estado"] = "normal"
        p["desc"] = round(100 * (1 - p["precio"] / p["precio_antes"])) if p["precio_antes"] else 0
        bonus = {"minimo": 25, "bajo": 15, "subio": -15}.get(p["estado"], 0)
        if p["grupo"] == "arriba":                 # ancho pero corto: suben en el orden
            t = normalizar(cfg, p["titulo"])
            bonus += max([v for w, v in cfg.get("prioridad_arriba", {}).items() if not w.startswith("_") and f" {w} " in t] or [0])
        p["oferta"] = round(p["confianza"] * 0.5 + min(p["desc"], 70) * 0.7 + bonus)
        p["mi_talla"] = es_mi_talla(cfg, p)
        ref = date.fromisoformat(ultima_lectura.get(p["fuente"]) or p["ultima_vez"])
        p["activo"] = (ref - date.fromisoformat(p["ultima_vez"])).days <= 3
        out.append(p)
    return out


# ---------- Principal ----------
def actualizar(grupos):
    cfg = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
    t0 = time.time()
    tareas = {"Falabella": lambda: falabella(cfg, grupos),
              "Paris": lambda: paris_ripley(cfg, grupos, "paris"),
              "Ripley": lambda: paris_ripley(cfg, grupos, "ripley"),
              "Shopify": lambda: shopify(cfg, grupos)}
    with ThreadPoolExecutor(len(tareas)) as ex:   # cada tienda en paralelo, cada una a su ritmo
        futuros = {k: ex.submit(f) for k, f in tareas.items()}
    c = db()
    resumen = []
    for k, fu in futuros.items():
        try:
            prods = fu.result()
        except Exception as e:
            log(f"! {k} fallo: {e}")
            prods = []
        n = 0
        for p in prods:
            if genero(p["titulo"], p.get("cat", "")) == "niño" or marca_excluida(cfg, p):
                continue
            guardar(c, p)
            n += 1
        resumen.append(f"{k}: {n}")
    c.commit()
    podar(c, cfg)
    colorear_fotos(c)
    log(f"\nActualizado en {round(time.time() - t0)}s  ->  " + " | ".join(resumen))
    log("Consultas hechas: " + ", ".join(f"{k}: {v}" for k, v in CONTEO.items()))
    return c, cfg


def generar_html(items):
    plantilla = (BASE / "plantilla.html").read_text(encoding="utf-8")
    datos = json.dumps(items, ensure_ascii=False).replace("</", "<" + chr(92) + "/")
    (BASE / "resultados.html").write_text(
        plantilla.replace("/*DATOS*/[]", datos).replace("{{FECHA}}", date.today().strftime("%d-%m-%Y")), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("grupo", nargs="?", choices=[*GRUPOS, "todo", "ver", "colores"], default="todo")
    a = ap.parse_args(argv)
    if a.grupo in ("ver", "colores"):
        c, cfg = db(), json.loads((BASE / "config.json").read_text(encoding="utf-8"))
        if a.grupo == "colores":
            colorear_fotos(c)
    else:
        c, cfg = actualizar(list(GRUPOS) if a.grupo == "todo" else [a.grupo])
    items = cargar_todo(c, cfg)
    generar_html(items)
    log(f"Pagina lista: {sum(p['activo'] for p in items)} productos vigentes. {BASE / 'resultados.html'}")


if __name__ == "__main__":
    sys.exit(main())
