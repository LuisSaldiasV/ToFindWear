# Revisión: lector de tiendas Shopify del comparador de ropa

Proyecto personal (no comercial): un script en Python que junta productos de tiendas chilenas, los filtra por estilo (baggy/boxy) y genera una página local con precios e historial. Cada tarjeta lleva a la tienda oficial.

Este documento contiene solo la parte que lee **tiendas Shopify** (Kagi, Treino, Dynamo, OVA, etc.). Todo está en `comparador.py`, sin dependencias externas: solo la biblioteca estándar.

## Cómo funciona

1. Para cada tienda de `config.json → tiendas_shopify`, se descarga el catálogo público `https://<tienda>/products.json?limit=250&page=N` hasta que una página trae menos de 250 productos.
2. Cada producto se clasifica en `abajo` / `arriba` / `zapatillas` según su título (`clasificar` → `cumple_estilo`). Si no calza en ninguno, se descarta.
3. Se guardan el precio mínimo de las variantes disponibles, el precio anterior (`compare_at_price`), las tallas y la primera imagen.
4. Todas las fuentes (Falabella, Paris, Ripley, Shopify) corren en hilos paralelos. Las tiendas Shopify, en cambio, se consultan **una tras otra** dentro de su hilo.

### Lo que ya sabemos del bloqueo (429)

- Shopify limita por **IP y para todas sus tiendas a la vez**, no por tienda. Tras una ráfaga de pruebas, todas respondían `429` con `Retry-After: 60`, incluso las páginas HTML normales.
- Reintentar alargaba el bloqueo. Por eso, en Shopify **no se reintenta**: al primer 429 se omiten todas las tiendas Shopify ese día y se conservan sus datos anteriores.
- Con el ritmo actual (4 s entre consultas a un mismo sitio, pocas páginas por tienda, una vez al día) no esperamos bloqueos, pero aún no está confirmado en uso normal.

## Configuración (`config.json`)

```json
"tiendas_shopify": {
  "kagi.cl": {"estilo_propio": true},
  "treino.cl": {"estilo_propio": true},
  "dynamobrand.co": {"estilo_propio": true},
  "ovachile.cl": {"estilo_propio": true},
  "hazeconcept.com": {"estilo_propio": true},
  "hardfly.cl": {"estilo_propio": true},
  "freshbrand.cl": {"estilo_propio": true},
  "www.vans.cl": {"estilo_propio": false}
}
```

`estilo_propio: true` significa que toda la marca es del estilo buscado: el producto entra solo por tipo de prenda, sin exigir "baggy/boxy" en el nombre. Las listas de exclusión se aplican igual.

## 1. Descarga con pausas (`comparador.py`, líneas 26–56)

```python
ESPERA = {"shopify": 4.0, "default": 2.0}   # segundos minimos entre consultas al mismo sitio
_ultima, _lock = {}, threading.Lock()


class Bloqueado(Exception):
    pass


def get(url, tipo="default"):
    host = urllib.parse.urlparse(url).netloc
    for intento in range(3):
        with _lock:
            espera = _ultima.get(host, 0) + ESPERA.get(tipo, 2.0) - time.time()
            _ultima[host] = time.time() + max(espera, 0)
        if espera > 0:
            time.sleep(espera)
        try:
            req = urllib.request.Request(url, headers=UA)
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
```

## 2. Filtro de estilo (líneas 65–92)

```python
def normalizar(cfg, titulo):
    t = titulo.lower()
    for frase in cfg.get("quitar_del_titulo", []):
        t = t.replace(frase, " ")
    return " " + re.sub(r"[^\w]+", " ", t) + " "


def cumple_estilo(cfg, grupo, titulo, estilo_propio=False):
    t = normalizar(cfg, titulo)
    regla = cfg["estilo"][grupo]
    hay = lambda w: (" " + re.sub(r"[^\w]+", " ", w).strip() + " ") in t or (len(w) > 5 and w in t)
    nunca = regla["nunca"] + (cfg.get("tiendas_estilo_nunca", []) if estilo_propio else [])
    if any(hay(w) for w in nunca):
        return False
    ns = regla.get("nunca_salvo")
    if ns and any(hay(w) for w in ns["palabras"]) and not any(hay(w) for w in ns["salvo"]):
        return False
    if not any(hay(w) for w in regla["tipo"]):
        return False
    return estilo_propio or any(hay(w) for w in regla["debe_tener"])


def clasificar(cfg, titulo, estilo_propio, grupos):
    """En que grupo cae un producto de una tienda que trae todo su catalogo."""
    for g in ("zapatillas", "abajo", "arriba"):
        if g in grupos and cumple_estilo(cfg, g, titulo, estilo_propio and g != "zapatillas"):
            return g
    return None
```

## 3. Lector Shopify (líneas 249–294)

```python
def shopify(cfg, grupos):
    out = []
    for dominio, opc in cfg.get("tiendas_shopify", {}).items():
        if dominio.startswith("_"):
            continue
        log(f"[Shopify] {dominio}")
        prods = []
        try:
            for pag in range(1, 20):
                lote = json.loads(get(f"https://{dominio}/products.json?limit=250&page={pag}", "shopify")).get("products", [])
                prods += lote
                if len(lote) < 250:
                    break
        except Bloqueado:
            log("  ! Shopify pidio pausa: hoy se omiten las tiendas Shopify (se mantienen sus datos anteriores)")
            break
        except Exception as e:
            log(f"  ! {dominio}: {e} (se mantienen sus datos anteriores)")
            continue
        fuente = dominio.removeprefix("www.")
        n = 0
        for x in prods:
            g = clasificar(cfg, x.get("title", "") + " " + (x.get("product_type") or ""), opc.get("estilo_propio"), grupos)
            if not g:
                continue
            vs = [v for v in x.get("variants", []) if v.get("available", True)]
            if not vs:
                continue
            precio = min(int(float(v["price"])) for v in vs)
            antes = max((int(float(v["compare_at_price"])) for v in vs if v.get("compare_at_price")), default=None)
            opciones = [o.get("name", "").lower() for o in x.get("options", [])]
            idx = next((i for i, o in enumerate(opciones) if any(k in o for k in ("talla", "size", "tamaño", "numero", "número"))), 0)
            tallas = []
            for v in vs:
                t = v.get(f"option{idx + 1}") or ""
                if t and t.lower() != "default title" and t not in tallas:
                    tallas.append(t)
            out.append({"fuente": fuente, "id": x["handle"], "titulo": x.get("title", ""),
                        "marca": x.get("vendor", "") or fuente, "vendedor": fuente, "oficial": True,
                        "precio": precio, "precio_antes": antes if antes and antes > precio else None,
                        "rating": None, "reviews": 0, "url": f"https://{dominio}/products/{x['handle']}",
                        "img": (x.get("images") or [{}])[0].get("src"), "tallas": tallas, "colores": [], "cat": "",
                        "grupo": g, "busqueda": "catalogo", "unisex": opc.get("estilo_propio")})
            n += 1
        log(f"  {dominio}: {len(prods)} en catalogo, {n} de tu estilo")
    return out
```

## Dónde nos sirve tu opinión

1. **Ritmo y bloqueos:** ¿basta con 4 s entre consultas, o conviene también recordar el último 429 (por ejemplo, en un archivo) y no volver a consultar Shopify durante unas horas?
2. **Menos datos:** ¿vale la pena leer solo colecciones específicas (`/collections/<nombre>/products.json`) en vez del catálogo completo? Serían menos consultas, pero los nombres de colección cambian en cada tienda.
3. **Clasificación:** hoy se usan solo `title` y `product_type`. ¿Agregar `tags` mejoraría la precisión sin meter ruido?
4. **Tallas:** si ninguna opción se llama talla/size/número, se usa la primera opción (`idx = 0`), que a veces es el color. ¿Lo dejamos así, o mejor dejar las tallas vacías?
5. **Precio:** `int(float(v["price"]))` asume que el precio viene como texto con punto decimal (`"24990.00"`). ¿Ves algún caso en que falle?
6. **Coincidencia de palabras en `hay`:** las palabras de más de 5 letras se buscan como texto parcial (`"ajustad"` también calza en `"ajustado"`). ¿Ves riesgo de falsos positivos?
