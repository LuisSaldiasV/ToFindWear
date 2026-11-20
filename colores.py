"""Detecta el color de cada prenda a partir de nombres de color (variante de la tienda o titulo).

Los hex son tonos realistas de ropa, no colores 'puros': el azul de una polera no es #0000FF.
'neutro' marca colores que combinan con casi todo (negro, blanco, grises, beige, denim...).
Para agregar un color: una linea en COLORES. Las frases mas largas ganan ("azul marino" antes que "azul").
"""
import re
import unicodedata

# nombre: (hex, neutro)
COLORES = {
    # negros / blancos / grises
    "negro": ("#1c1c1e", True), "black": ("#1c1c1e", True), "washed black": ("#3a3a3c", True), "negro lavado": ("#3a3a3c", True),
    "carbon": ("#333438", True), "grafito": ("#41434a", True), "charcoal": ("#36393f", True),
    "gris oscuro": ("#4a4c52", True), "gris": ("#8a8c91", True), "grey": ("#8a8c91", True), "gray": ("#8a8c91", True),
    "gris claro": ("#c4c5c8", True), "melange": ("#a3a4a6", True), "gris melange": ("#a3a4a6", True), "heather grey": ("#a3a4a6", True),
    "plomo": ("#7d7f84", True), "acero": ("#6d7680", True), "ash": ("#b2b2ad", True),
    "blanco": ("#f4f4f1", True), "white": ("#f4f4f1", True), "blanco humo": ("#ebeae4", True), "off white": ("#ece8dc", True),
    "marfil": ("#ede6d3", True), "ivory": ("#ede6d3", True), "hueso": ("#e6dfcd", True), "crudo": ("#e3dac4", True),
    "crema": ("#eadfc4", True), "cream": ("#eadfc4", True), "ecru": ("#ddd2b6", True),
    # beige / cafes / tierra
    "beige": ("#d6c4a3", True), "arena": ("#cdb995", True), "sand": ("#cdb995", True), "stone": ("#bdb3a1", True),
    "khaki": ("#b5a47a", True), "kaki": ("#b5a47a", True), "caqui": ("#b5a47a", True), "taupe": ("#8b7d6b", True),
    "camel": ("#b08455", False), "tostado": ("#a8794e", False), "tabaco": ("#7a5233", False), "cafe": ("#5e4130", True),
    "cafe oscuro": ("#3e2b20", True), "cafe claro": ("#9a7556", False), "marron": ("#5e4130", True), "brown": ("#5e4130", True),
    "chocolate": ("#4a3023", True), "moca": ("#6f5442", True), "mocha": ("#6f5442", True), "terracota": ("#b5603f", False),
    "oxido": ("#9c4f2e", False), "rust": ("#9c4f2e", False), "cobre": ("#a8643c", False), "mostaza": ("#c79a2e", False),
    # azules
    "azul marino": ("#1f2a44", True), "marino": ("#1f2a44", True), "navy": ("#1f2a44", True), "azul oscuro": ("#26355a", True),
    "azul": ("#3a5a8c", False), "blue": ("#3a5a8c", False), "azul rey": ("#2b4ca8", False), "royal": ("#2b4ca8", False),
    "indigo": ("#2e3a6b", True), "azul petroleo": ("#1f4f5c", False), "petroleo": ("#1f4f5c", False),
    "azul claro": ("#8fb0d4", False), "celeste": ("#a7c7e3", False), "light blue": ("#a7c7e3", False), "sky": ("#a7c7e3", False),
    "turquesa": ("#3fa7a6", False), "teal": ("#2f7f7c", False), "aqua": ("#7cc6c4", False),
    # denim (se trata como neutro, como en la moda real)
    "denim": ("#4a6385", True), "mezclilla": ("#4a6385", True), "azul denim": ("#4a6385", True),
    "light wash": ("#8ea6c2", True), "lavado claro": ("#8ea6c2", True), "dark wash": ("#2c3c57", True), "lavado oscuro": ("#2c3c57", True),
    "stone wash": ("#7c93b0", True), "vintage blue": ("#6a84a6", True),
    # verdes
    "verde": ("#3f6b4a", False), "green": ("#3f6b4a", False), "verde oliva": ("#6b6b3a", True), "oliva": ("#6b6b3a", True),
    "olive": ("#6b6b3a", True), "militar": ("#545a3a", True), "verde militar": ("#545a3a", True), "army": ("#545a3a", True),
    "musgo": ("#5c6a3c", False), "salvia": ("#9aa98a", False), "sage": ("#9aa98a", False), "menta": ("#a9d6bf", False),
    "verde botella": ("#1f4a35", False), "verde oscuro": ("#24412f", False), "esmeralda": ("#1f7a55", False),
    "verde agua": ("#9ccfbf", False), "pistacho": ("#b9c98a", False), "lima": ("#b4cc4a", False),
    # rojos / rosas / morados
    "rojo": ("#b0302e", False), "red": ("#b0302e", False), "burdeo": ("#6b1f2a", False), "burdeos": ("#6b1f2a", False),
    "burgundy": ("#6b1f2a", False), "vino": ("#5e1c28", False), "granate": ("#6e2230", False), "cereza": ("#8e1f33", False),
    "coral": ("#e07a65", False), "salmon": ("#e8967f", False), "rosa": ("#e3a5b4", False), "rosado": ("#e3a5b4", False),
    "pink": ("#e3a5b4", False), "rosa palo": ("#dcb6b0", False), "fucsia": ("#c2337a", False), "magenta": ("#b0306f", False),
    "morado": ("#5b3b78", False), "purple": ("#5b3b78", False), "violeta": ("#6c4a96", False), "lila": ("#b7a2cf", False),
    "lavanda": ("#b9addb", False), "lavender": ("#b9addb", False), "berenjena": ("#3f2433", False),
    # amarillos / naranjos
    "amarillo": ("#e2c34a", False), "yellow": ("#e2c34a", False), "ocre": ("#c08a2e", False), "dorado": ("#c4a24c", False),
    "naranja": ("#e07a2e", False), "naranjo": ("#e07a2e", False), "orange": ("#e07a2e", False), "durazno": ("#f0b48f", False),
    "peach": ("#f0b48f", False), "damasco": ("#eeae7e", False),
}

# Palabras que indican que no hay un color unico
SIN_COLOR = ("multicolor", "estampado", "animal print", "print", "surtido", "tie dye", "camuflado", "camo", "rayas", "cuadros", "check")

DENIM = ("jean", "jeans", "jort", "jorts", "denim", "mezclilla")


def _norm(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    t = re.sub(r"\d+", " ", t)                 # "azul 2" -> "azul"
    return " " + re.sub(r"[^a-z]+", " ", t).strip() + " "


_ORDEN = sorted(COLORES, key=len, reverse=True)


def buscar(texto):
    """Primer color reconocido en un texto (la frase mas larga gana). None si no hay."""
    m = re.fullmatch(r"\s*#([0-9a-fA-F]{6})\s*", texto or "")
    if m:                                      # la tienda ya dio el hex como nombre
        h = "#" + m.group(1).lower()
        r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
        return {"n": h, "hex": h, "neutro": max(r, g, b) - min(r, g, b) < 25}
    t = _norm(texto)
    if any(" " + s + " " in t for s in SIN_COLOR):
        return None
    for nombre in _ORDEN:
        if " " + nombre + " " in t:
            hexa, neutro = COLORES[nombre]
            return {"n": nombre, "hex": hexa, "neutro": neutro}
    return None


def detectar(p):
    """Lista de colores de una prenda: uno por variante de color si la tienda los da, si no desde el titulo.

    Cada item: {n, hex, neutro, origen, k}  (k = indice de la variante en p['colores'], o None)
    origen: 'variante' (nombre que da la tienda), 'titulo' (encontrado en el nombre del producto),
            'supuesto' (jeans sin color -> denim).
    """
    out = []
    for k, v in enumerate(p.get("colores") or []):
        c = buscar(v.get("n"))
        if c:
            out.append(dict(c, origen="variante", k=k))
    if out:
        return out
    c = buscar(p.get("titulo"))
    if c:
        return [dict(c, origen="titulo", k=None)]
    t = _norm(p.get("titulo"))
    if p.get("grupo") == "abajo" and any(" " + d + " " in t for d in DENIM):
        hexa, _ = COLORES["denim"]
        return [{"n": "denim", "hex": hexa, "neutro": True, "origen": "supuesto", "k": None}]
    return []
