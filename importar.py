"""Importa catalogos de tiendas Shopify guardados desde tu navegador.

Esas tiendas bloquean la lectura automatica, pero no a ti navegando. El marcador
"Guardar catalogo TFW" (ver MARCADOR abajo y el README) descarga, desde la tienda que
tienes abierta, un archivo tfw_<tienda>.json con su catalogo. comparador.py busca esos
archivos en la carpeta importar/ y en tu carpeta Descargas, los procesa y los mueve a
importar/procesados/.
"""
import json, shutil
from datetime import datetime
from pathlib import Path

CARPETA = Path(__file__).parent / "importar"
DESCARGAS = Path.home() / "Downloads"

# Se pega como direccion (URL) de un marcador del navegador. Corre solo cuando tu lo apretas,
# en la tienda que estas viendo: pide su catalogo publico pagina por pagina, con pausa, y lo descarga.
MARCADOR = (
    "javascript:(async()=>{let a=[];for(let p=1;p<=20;p++){let r=await fetch('/products.json?limit=250&page='+p);"
    "if(!r.ok){alert('TFW: esta pagina no es una tienda Shopify o no dejo leer el catalogo ('+r.status+')');return}"
    "let j=await r.json();a=a.concat(j.products||[]);if(!j.products||j.products.length<250)break;"
    "await new Promise(s=>setTimeout(s,1500))}"
    "let b=new Blob([JSON.stringify({tienda:location.hostname,fecha:new Date().toISOString(),products:a})],{type:'application/json'});"
    "let l=document.createElement('a');l.href=URL.createObjectURL(b);l.download='tfw_'+location.hostname+'.json';"
    "document.body.appendChild(l);l.click();l.remove();alert('TFW: '+a.length+' productos de '+location.hostname+' guardados')})()"
)


def archivos():
    """Archivos tfw_*.json pendientes (incluye los que el navegador numera, ej. 'tfw_kagi.cl (1).json')."""
    out = []
    for carpeta in (CARPETA, DESCARGAS):
        if carpeta.is_dir():
            out += sorted(carpeta.glob("tfw_*.json"))
            out += sorted(carpeta.glob("*/tfw_*.json"))   # tambien en subcarpetas directas (ej. Descargas/catalogos)
    return [r for r in out if "procesados" not in r.parts]


def leer(ruta):
    """(tienda, productos) de un archivo; None si no tiene el formato esperado."""
    try:
        d = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict) or not isinstance(d.get("products"), list) or not d.get("tienda"):
        return None
    return d["tienda"], d["products"]


def archivar(ruta):
    """Mueve el archivo ya procesado a importar/procesados/ (con fecha, para no pisar uno anterior)."""
    destino = CARPETA / "procesados"
    destino.mkdir(parents=True, exist_ok=True)
    shutil.move(str(ruta), destino / f"{datetime.now():%Y%m%d-%H%M%S}_{ruta.name}")


def pagina_ayuda():
    """Crea importar/importar.html: el marcador para arrastrar y los enlaces a tus tiendas."""
    import html
    cfg = json.loads((Path(__file__).parent / "config.json").read_text(encoding="utf-8"))
    tiendas = [d for d in cfg.get("tiendas_shopify", {}) if not d.startswith("_")]
    enlaces = "".join(f'<li><a href="https://{html.escape(d)}" target="_blank">{html.escape(d)}</a></li>' for d in tiendas)
    CARPETA.mkdir(exist_ok=True)
    ruta = CARPETA / "importar.html"
    ruta.write_text(f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Importar tiendas</title>
<style>body{{font-family:system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px;line-height:1.55;background:#f6f6f4;color:#1c1c1e}}
.m{{display:inline-block;padding:10px 16px;border-radius:10px;background:#ff5a36;color:#fff;font-weight:600;text-decoration:none}}
li{{margin:4px 0}} code{{background:#e8e8e4;padding:1px 5px;border-radius:4px}}</style></head><body>
<h1>Importar tiendas desde tu navegador</h1>
<h2>1. Instala el marcador (solo la primera vez)</h2>
<p>Muestra la barra de favoritos con <code>Ctrl+Shift+B</code> y <b>arrastra este botón</b> hasta ella:</p>
<p><a class="m" href="{html.escape(MARCADOR)}">Guardar catálogo TFW</a></p>
<h2>2. Guarda cada tienda</h2>
<p>Abre una tienda, espera a que cargue y aprieta el marcador. Se descarga <code>tfw_tienda.json</code> en Descargas y te avisa cuántos productos guardó.</p>
<ul>{enlaces}</ul>
<p>Sirve en cualquier tienda hecha con Shopify (por ejemplo, otra marca chilena que te guste), aunque no esté en la lista.</p>
<h2>3. Carga lo guardado</h2>
<p>En <code>abrir.bat</code> elige <b>8) Procesar catálogos guardados</b>. También se procesan solos en la actualización diaria.</p>
</body></html>""", encoding="utf-8")
    return ruta


if __name__ == "__main__":
    import webbrowser
    webbrowser.open(pagina_ayuda().as_uri())
