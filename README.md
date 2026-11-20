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

Requiere Python 3. No necesita instalar dependencias.

```bash
python comparador.py              # actualiza todo
python comparador.py abajo        # solo pantalones / jorts / buzos
python comparador.py arriba       # solo parte superior
python comparador.py zapatillas   # solo zapatillas
python comparador.py ver          # no busca, solo regenera la página
```

En Windows también puedes usar `abrir.bat`, que muestra un menú.

### Actualización automática

`actualizar_diario.pyw` se ejecuta al iniciar Windows, sin abrir ventana. Actualiza el catálogo una vez al día y deja el registro en `log.txt`.

## Configuración

En `config.json` se ajustan las búsquedas de cada grupo y los filtros. Las palabras se comparan sin distinguir mayúsculas.

## Estructura

| Archivo | Para qué sirve |
|---|---|
| `comparador.py` | Búsqueda, filtrado, historial y generación del HTML |
| `colores.py` | Detección y agrupación de colores |
| `importar.py` | Importa productos de forma manual |
| `plantilla.html` | Plantilla de la página de resultados |
| `wada.js` | Paleta de Sanzo Wada (datos MIT, © Matt DesLauriers) |
| `netlify.toml` | Publicación en Netlify (`/` abre `resultados.html`) |

## Despliegue

El repo está conectado a Netlify: cada push a `main` vuelve a publicar la página.
En el celular, abre la URL y elige **"Agregar a pantalla de inicio"**.

## Notas

Las consultas a las tiendas van espaciadas (2 a 4 s entre una y otra) para no saturar los sitios ni provocar bloqueos.
