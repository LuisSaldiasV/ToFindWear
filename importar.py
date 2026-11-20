"""Importa productos desde paginas guardadas (HAR o HTML) de tiendas que bloquean lectura automatica.

Deja los archivos en la carpeta importar/ (por ejemplo, guardando la pagina con Ctrl+S
como 'Pagina web, solo HTML', o un .har). comparador.py los procesa solo y despues
los mueve a importar/procesados/.
"""
import html, json, re, shutil
from pathlib import Path

CARPETA = Path(__file__).parent / "importar"


def paginas(ruta):
    """Devuelve (url_base, html) de cada pagina dentro de un .har o .html."""
    if ruta.suffix.lower() == ".har":
        h = json.loads(ruta.read_text(encoding="utf-8"))
        for e in h["log"]["entries"]:
            ct = e["response"]["content"].get("mimeType", "")
            txt = e["response"]["content"].get("text") or ""
            if "html" in ct and len(txt) > 20000:  # solo paginas completas, nada de cookies
                yield e["request"]["url"], txt
    else:
        txt = ruta.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'<link rel="canonical" href="([^"]+)"', txt)
        yield (m.group(1) if m else ""), txt


def precio(t):
    return int(re.sub(r"\D", "", t)) if re.sub(r"\D", "", t) else None


def kagi(url, txt):
    out = []
    for m in re.finditer(r"<li class='kagi-card' data-sz='([^']*)' data-av='(\w+)'>(.*?)</li>", txt, re.S):
        if m.group(2) != "true":
            continue
        b = m.group(3)
        tit = re.search(r"kagi-card__title'>(.*?)<", b)
        href = re.search(r"href='([^']+)'", b)
        img = re.search(r'<img src="([^"]+)"', b)
        pr = [precio(p) for p in re.findall(r"class=money>([^<]+)<", b)]
        pr = [p for p in pr if p]
        if not (tit and href and pr):
            continue
        handle = href.group(1).rstrip("/").split("/")[-1]
        out.append({
            "fuente": "kagi.cl", "id": handle, "titulo": html.unescape(tit.group(1)).strip(),
            "marca": "Kagi", "vendedor": "kagi.cl", "oficial": True,
            "precio": min(pr), "precio_antes": max(pr) if len(pr) > 1 and max(pr) > min(pr) else None,
            "rating": None, "reviews": 0, "cat": "",
            "url": "https://kagi.cl/products/" + handle,
            "img": ("https:" + html.unescape(img.group(1))) if img else None,
            "tallas": [s for s in m.group(1).split(",") if s], "colores": [],
        })
    return out


LECTORES = [("kagi-card", kagi)]


def leer_todo():
    """Lee los archivos de importar/ y devuelve (productos, archivos_leidos)."""
    prods, vistos, archivos = [], set(), []
    for ruta in sorted(CARPETA.glob("*")):
        if ruta.suffix.lower() not in (".har", ".html", ".htm"):
            continue
        archivos.append(ruta)
        for url, txt in paginas(ruta):
            for marca, lector in LECTORES:
                if marca in txt:
                    for p in lector(url, txt):
                        if (p["fuente"], p["id"]) not in vistos:
                            vistos.add((p["fuente"], p["id"]))
                            prods.append(p)
    return prods, archivos


def archivar(archivos):
    (CARPETA / "procesados").mkdir(exist_ok=True)
    for r in archivos:
        if r.suffix.lower() == ".har":
            r.unlink()  # el HAR puede traer cookies de sesion: no lo guardamos
        else:
            shutil.move(str(r), CARPETA / "procesados" / r.name)
