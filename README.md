# ToFindWear (TFW)

Comparador de precios de ropa en Chile, enfocado en el estilo **baggy / boxy / oversize**.
Busca en tiendas oficiales, filtra lo que no calza con el estilo y genera una página web con los mejores precios y su historial.

## Qué hace

- Busca productos en tres grupos: **abajo** (jeans baggy, wide leg, jorts, buzos), **arriba** (poleras boxy, polerones y chaquetas oversize) y **zapatillas**.
- Usa solo tiendas oficiales. No incluye fast fashion.
- Deja fuera los cortes que no van con el estilo (straight, jogger, etc.).
- Guarda el historial de precios en SQLite (`precios.db`), así puedes ver si un precio bajó de verdad.
- Genera `resultados.html`, una página estática que se publica en Netlify y se puede instalar en el celular.
- Incluye combinaciones de colores de Sanzo Wada (*A Dictionary of Colour Combinations*) para armar outfits.

## Uso

Requiere Python 3. Opcional: **Pillow** (`pip install pillow`) para leer el color de cada prenda desde su foto; sin Pillow se usan solo los nombres de color de las tiendas.

```bash
python comparador.py              # actualiza todo
python comparador.py abajo        # solo pantalones / jorts / buzos
python comparador.py arriba       # solo parte superior
python comparador.py zapatillas   # solo zapatillas
python comparador.py ver          # no busca, solo regenera la página
python comparador.py colores      # no busca, mide colores de fotos nuevas y regenera
```

En Windows también puedes usar `abrir.bat`, que muestra un menú.

### Actualización automática

`actualizar_diario.pyw` se ejecuta al iniciar Windows, sin abrir ventana. Actualiza el catálogo una vez al día y deja el registro en `log.txt`.

### Tiendas Shopify (Kagi, Haze Concept...)

Estas tiendas bloquean la lectura automática, así que se importan desde tu navegador:

1. En `abrir.bat`, elige **7**. Se abre una página con el marcador **Guardar catálogo TFW**: arrástralo a la barra de favoritos (solo la primera vez).
2. Abre cada tienda y aprieta el marcador. Se descarga `tfw_<tienda>.json` en Descargas.
3. En `abrir.bat`, elige **8** (o espera la actualización diaria). Los archivos se procesan y se mueven a `importar/procesados/`.

El marcador sirve en cualquier tienda hecha con Shopify, aunque no esté en `config.json`.

## Configuración

En `config.json` se ajustan las búsquedas de cada grupo y los filtros. Las palabras se comparan sin distinguir mayúsculas.

## Estructura

| Archivo | Para qué sirve |
|---|---|
| `comparador.py` | Búsqueda, filtrado, historial y generación del HTML |
| `colores.py` | Detección y agrupación de colores |
| `importar.py` | Importa catálogos de tiendas Shopify guardados desde el navegador |
| `plantilla.html` | Plantilla de la página de resultados |
| `wada.js` | Paleta de Sanzo Wada (datos MIT, © Matt DesLauriers) |
| `netlify.toml` | Publicación en Netlify (`/` abre `resultados.html`) |

## Despliegue

El repo está conectado a Netlify: cada push a `main` vuelve a publicar la página.
En el celular, abre la URL y elige **"Agregar a pantalla de inicio"**.

## Notas

Las consultas a las tiendas van espaciadas (2 a 4 s entre una y otra) para no saturar los sitios ni provocar bloqueos.

## Protecciones y herramientas
- **Revisión de `config.json`:** antes de cada corrida se revisa el archivo. Si tiene un error (por ejemplo, una coma de más), no se actualiza nada y se indica la línea. En la actualización automática aparece una ventana de aviso.
- **Tiendas caídas:** se guarda cuántos productos trae cada tienda por día. Si una trae menos del 40 % de lo normal, queda un aviso en `log.txt` y sus datos anteriores se mantienen. La limpieza de productos viejos se cuenta desde la última lectura buena de cada tienda.
- **Barra de estado:** bajo los filtros de la página se ve cuándo se leyó cada tienda. Las importadas con el marcador muestran "reimportar" cuando tienen más de 7 días.
- **Favoritos y ocultos:** cada producto tiene los botones ☆ y ✕, y el selector de vista permite ver solo favoritos o recuperar los ocultos. Se guardan en el navegador.
- **Pruebas del filtro:** `python test_estilo.py`. Conviene correrlas después de editar `config.json`. Si se cuela un producto, agrega su título a la lista de casos.
