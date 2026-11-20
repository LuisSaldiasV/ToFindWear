"""Color de una prenda leido desde su foto (requiere Pillow; si no esta, no hace nada).

Idea: achicar la foto, quitar el fondo (el color de los bordes), mirar solo la zona donde suele
estar la prenda segun el grupo (en fotos con modelo: torso para 'arriba', piernas para 'abajo'),
quitar piel, y quedarse con el color dominante. Luego se le pone el nombre de color mas cercano.
"""
import io, math, threading, time, urllib.error, urllib.parse, urllib.request

try:
    from PIL import Image
except ImportError:          # sin Pillow: se sigue usando solo el nombre que da la tienda
    Image = None

import colores

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36"}

# pausa minima entre imagenes del mismo sitio (Ripley responde 429 si se piden seguidas)
PAUSA = {"rimage.ripley.cl": 1.5, "home.ripley.cl": 1.5}
_ultima, _frenados, _lock = {}, set(), threading.Lock()


def _bajar(u, timeout):
    host = urllib.parse.urlparse(u).netloc
    with _lock:
        if host in _frenados:
            raise RuntimeError("sitio frenado en esta corrida")
        espera = _ultima.get(host, 0) + PAUSA.get(host, 0.25) - time.time()
        _ultima[host] = time.time() + max(espera, 0)
    if espera > 0:
        time.sleep(espera)
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code in (429, 503):     # no insistir: el resto queda para la proxima corrida
            _frenados.add(host)
        raise


# zona de la foto donde mirar: (x0, y0, x1, y1) en fracciones del ancho/alto
ZONA = {"arriba": (0.25, 0.25, 0.75, 0.58), "abajo": (0.25, 0.45, 0.75, 0.88), "zapatillas": (0.1, 0.2, 0.9, 0.85)}


def disponible():
    return Image is not None


def _lab(rgb):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = map(lin, rgb)
    f = lambda t: math.cbrt(t) if t > 0.008856 else 7.787 * t + 16 / 116
    x = f((r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047)
    y = f(r * 0.2126 + g * 0.7152 + b * 0.0722)
    z = f((r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883)
    return 116 * y - 16, 500 * (x - y), 200 * (y - z)


def _dist(a, b):
    return math.dist(_lab(a), _lab(b))


def _piel(rgb):
    r, g, b = rgb
    return r > 95 and g > 40 and b > 20 and r > g > b and 12 < r - g < 75 and r - b > 30 and max(rgb) - min(rgb) < 120


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


_PALETA = [(n, tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)), neu) for n, (h, neu) in colores.COLORES.items()]


def nombre_cercano(rgb):
    """Nombre del color de la lista mas parecido al rgb medido."""
    L, a, b = _lab(rgb)

    def d(x):   # la luz pesa la mitad: las sombras de la foto oscurecen, pero no cambian el tono
        L2, a2, b2 = _lab(x[1])
        return math.hypot((L - L2) * 0.5, a - a2, b - b2)
    n, _, neu = min(_PALETA, key=d)
    return n, neu or math.hypot(a, b) < 10


def dominante(datos, grupo):
    """rgb dominante de la prenda en la imagen (bytes). None si no se pudo."""
    im = Image.open(io.BytesIO(datos)).convert("RGB")
    im.thumbnail((120, 120))
    w, h = im.size
    px = im.load()
    borde = [px[x, y] for x in range(w) for y in (0, 1, h - 2, h - 1)] + [px[x, y] for y in range(h) for x in (0, 1, w - 2, w - 1)]
    fondo = tuple(sorted(c[i] for c in borde)[len(borde) // 2] for i in range(3))
    x0, y0, x1, y1 = ZONA.get(grupo, (0.2, 0.2, 0.8, 0.8))
    sel = []
    for y in range(int(y0 * h), int(y1 * h)):
        for x in range(int(x0 * w), int(x1 * w)):
            c = px[x, y]
            if math.dist(c, fondo) < 28:
                continue
            if grupo != "zapatillas" and _piel(c):
                continue
            sel.append(c)
    if len(sel) < 40:                     # casi todo era fondo: prenda del mismo tono que el fondo
        sel = [px[x, y] for y in range(int(y0 * h), int(y1 * h)) for x in range(int(x0 * w), int(x1 * w))]
    mini = Image.new("RGB", (len(sel), 1))
    mini.putdata(sel)
    q = mini.quantize(colors=5, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    cuenta = sorted(q.getcolors(), reverse=True)
    n, i = cuenta[0]
    return tuple(pal[i * 3:i * 3 + 3])


def color_de_foto(url, grupo, timeout=20):
    """{'n', 'hex', 'neutro'} medido en la foto, o None si falla. Prueba _1 <-> _01 en Falabella."""
    if not Image or not url:
        return None
    urls = [url]
    if "media.falabella.com" in url:
        urls.append(url.replace("_1/public", "_01/public") if "_1/public" in url else url.replace("_01/public", "_1/public"))
    for u in urls:
        try:
            datos = _bajar(u, timeout)
            rgb = dominante(datos, grupo)
        except Exception:
            continue
        n, neu = nombre_cercano(rgb)
        return {"n": n, "hex": _hex(rgb), "neutro": neu, "url": u}
    return None
