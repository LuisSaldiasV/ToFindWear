# Instrucciones para el asistente de IA — Revisión y plan de arreglo del lector Shopify

## Contexto del proyecto

Proyecto personal, no comercial. Script Python en `comparador.py` (solo stdlib, sin dependencias externas) que junta productos de tiendas chilenas, los filtra por estilo (baggy/boxy) y genera una página local con precios e historial. Cada tarjeta lleva a la tienda oficial.

Este documento cubre **solo la parte que lee tiendas Shopify** (Kagi, Treino, Dynamo, OVA, Haze, Hardfly, Fresh Brand, Vans Chile) definidas en `config.json → tiendas_shopify`.

## Tu tarea

Revisar el código actual del lector Shopify, contrastarlo con las observaciones y mejoras propuestas abajo, y **entregar un plan de cambios priorizado y concreto** (no implementar todavía, salvo que se pida). El plan debe indicar: qué archivo/función/línea tocar, qué cambio hacer, por qué, y cómo verificar que funciona.

No introduzcas dependencias externas. No cambies la filosofía actual: una corrida diaria, stdlib, sin reintentos agresivos en Shopify.

## Cómo funciona hoy (para ubicarte)

1. Para cada tienda de `config.json → tiendas_shopify`, descarga `https://<tienda>/products.json?limit=250&page=N` hasta que una página trae menos de 250 productos.
2. Clasifica cada producto en `abajo` / `arriba` / `zapatillas` según título (`clasificar` → `cumple_estilo`). Si no calza, se descarta.
3. Guarda precio mínimo de variantes disponibles, precio anterior (`compare_at_price`), tallas y primera imagen.
4. Todas las fuentes corren en hilos paralelos; las tiendas Shopify se consultan una tras otra dentro de su hilo.

### Lo que ya sabemos del bloqueo (429)

- Shopify limita **por IP y para todas sus tiendas a la vez**, no por tienda. Tras una ráfaga de pruebas, todas respondían `429` con `Retry-After: 60`, incluso páginas HTML normales.
- Reintentar alargaba el bloqueo. Por eso en Shopify **no se reintenta**: al primer 429 se omiten todas las tiendas Shopify ese día y se conservan sus datos anteriores.
- Con el ritmo actual (4 s entre consultas a un mismo sitio, pocas páginas por tienda, una vez al día) no se esperan bloqueos, pero **no está confirmado en uso normal**.

### Configuración (`config.json`)

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

`estilo_propio: true`: toda la marca es del estilo buscado; el producto entra solo por tipo de prenda, sin exigir "baggy/boxy" en el nombre. Las listas de exclusión se aplican igual.

## Código actual relevante

### A. Descarga con pausas (`comparador.py`, líneas ~26–56)

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

### B. Filtro de estilo (líneas ~65–92)

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

### C. Lector Shopify (líneas ~249–294)

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

## Cambios propuestos (verificar y priorizar)

El plan debe evaluar cada punto, decidir si aplica, y si aplica, describir el cambio exacto.

### Prioridad alta

1. **Enfriamiento global persistido en disco tras 429.**
   - Hoy el "no reintentar" solo dura lo que dura el proceso. Si relanzas el script, vuelves a golpear la IP bloqueada.
   - Propuesta: archivo de estado (ej. `.shopify_estado.json`) con `{"bloqueado_hasta": timestamp}`. Al inicio de `shopify()`, si `time.time() < bloqueado_hasta`, omitir todas las tiendas Shopify y conservar datos. Al atrapar `Bloqueado`, guardar `bloqueado_hasta = now + max(Retry-After, 3600)`.
   - Usar `Retry-After` de la respuesta 429 (hoy se descarta para Shopify). Es la señal más fiable.
   - Verificación: simular 429 (mock o URL inválida), relanzar el script y confirmar que no hace requests a Shopify y loguea el enfriamiento.

2. **Tallas: no usar `idx = 0` como fallback.**
   - Hoy si la primera opción es "Color", se guardan colores como tallas.
   - Propuesta: `idx = next(..., None)`; si `idx is None`, `tallas = []`.
   - Verificación: producto con opciones `["Color","Talla"]` y producto con solo `["Color"]`; el segundo debe quedar con `tallas == []`.

3. **Parseo robusto de precios.**
   - Hoy `int(float(v["price"]))` falla con `None`, `""`, `"24.990,00"`, `"$ 24990"`.
   - Propuesta: helper `a_int(precio)` que devuelva `None` ante entrada inválida; filtrar variantes sin precio válido antes de `min()`/`max()`; si no queda ninguna, `continue`.
   - Verificación: casos unitarios con `"24990.00"`, `None`, `""`, `"24990,00"`, `"$ 24.990"`.

### Prioridad media

4. **Espaciado global entre requests a Shopify, no solo por host.**
   - El límite es por IP y agregado entre tiendas; el espaciado por host no protege del agregado.
   - Propuesta: un timestamp global `_ultimo_shopify` + `esperar_shopify_global(minimo=2.0)` llamado antes de cada `get(..., "shopify")`. Serializa el tráfico a Shopify.
   - Verificación: log de timestamps entre requests consecutivos a distintas tiendas Shopify; deben respetar el mínimo global.

5. **`tags` como señal positiva en la clasificación.**
   - `tags` suele traer "baggy", "oversize", "boxy", "wide leg".
   - Propuesta: concatenar `title + product_type + tags` para `tipo` y `debe_tener`; mantener `nunca` solo sobre `title + product_type` (más conservador). Adaptar `cumple_estilo` para recibir dos textos (`texto_pos`, `texto_neg`).
   - Verificación: producto con título neutro y tag "baggy" debe entrar como `abajo`; producto con tag "slim" en título neutro **no** debe excluirse solo por el tag.

6. **`hay`: exacto para exclusiones, parcial para positivas.**
   - Hoy el parcial (>5 letras) se aplica también a `nunca`, con riesgo de excluir de más.
   - Propuesta: `hay(w, parcial=True)`; en `nunca` y `nunca_salvo.palabras` usar `parcial=False`. Mantener parcial en `tipo` y `debe_tener`.
   - Verificación: lista de títulos con palabras que sean prefijo de otras; confirmar que exclusiones ya no matchean por prefijo.

### Prioridad baja

7. **Validar tipo de `products` en cada página.**
   - Hoy `.get("products", [])` enmascara respuestas inesperadas y corta la paginación perdiendo productos.
   - Propuesta: si `products` no es `list`, lanzar `ValueError` y tratar como error de esa tienda (conservar datos anteriores).
   - Verificación: respuesta `{"error": "..."}` debe loguear error y no truncar silenciosamente.

8. **Deduplicar por `handle` antes de clasificar.**
   - Propuesta: `vistos = set()`; saltar si `x["handle"]` ya visto.
   - Verificación: catálogo con handle repetido entre páginas.

9. **Fallback a colecciones si `products.json` da 403/404 persistente.**
   - Solo como ruta alternativa, no principal. `GET /collections.json` (una llamada) y luego `/collections/<handle>/products.json?limit=250&page=N`.
   - Verificación: tienda cuyo `products.json` devuelve 403; confirmar que el fallback obtiene productos.

10. **Acotar `range(1, 20)`.**
    - 20 páginas × 250 = 5.000 productos por tienda. Para tiendas de ropa chilenas es holgado; considerar `range(1, 12)` (3.000) para acotar daño.
    - Verificación: tienda con >3.000 productos debe loguear truncamiento explícito.

11. **UA y headers.**
    - Confirmar que `UA` es un UA de navegador realista y consistente; agregar `Accept: application/json` en requests a Shopify.
    - Verificación: comparar tasa de 403 antes/después.

12. **Log de presupuesto por corrida.**
    - Contar requests a Shopify en la corrida y loguear al inicio/fin. Sirve para calibrar el espaciado real contra el límite observado.

## Restricciones

- Solo stdlib. No agregar `requests`, `httpx`, `aiohttp`, etc.
- No romper el contrato de salida: cada producto debe seguir teniendo `fuente`, `id`, `titulo`, `marca`, `vendedor`, `oficial`, `precio`, `precio_antes`, `rating`, `reviews`, `url`, `img`, `tallas`, `colores`, `cat`, `grupo`, `busqueda`, `unisex`.
- No cambiar la política de "no reintentar en Shopify" salvo el enfriamiento persistido (punto 1), que **extiende** esa política, no la contradice.
- Cambios de clasificación (puntos 5 y 6) deben ser retrocompatibles: si una tienda no trae `tags`, el comportamiento debe ser equivalente al actual (salvo el cambio de parcialidad en exclusiones, que es intencional).

## Entregable esperado

Un plan en Markdown con:

1. **Tabla de cambios priorizados**: prioridad, punto (1–12), archivo/función, resumen del cambio, riesgo, esfuerzo (S/M/L).
2. **Orden de implementación sugerido**, agrupando cambios que tocan la misma función para minimizar conflictos.
3. **Plan de pruebas**: por cada cambio, un caso concreto (entrada → salida esperada) que se pueda verificar sin red (usando datos de ejemplo) o con una tienda real.
4. **Preguntas abiertas** para el dueño del proyecto: decisiones que dependen de su criterio (ej. duración del enfriamiento, si aceptar el fallback a colecciones, si `tags` puede excluir).

No implementes todavía. Primero el plan; luego, si se aprueba, se implementa por bloques.