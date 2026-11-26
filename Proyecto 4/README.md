# Cafetería Brisa – Tiendita 24/7 (Programación IV, Proyecto 4)

Tienda web con inventario y ventas en tiempo real. Soporta millones de ventas históricas
(Parquet + Polars) y hace un corte de caja automático sin detener la API.

## Qué se implementó en cada unidad
| Unidad | Qué se hizo |
|---|---|
| 1. API y cliente web | Servidor REST con FastAPI y cliente HTML/CSS/JS con `fetch()` |
| 2. Concurrencia y fallas | Validación con Pydantic, errores HTTP (400, 404) y `asyncio.Lock()` contra condiciones de carrera |
| 3. Persistencia y visualización | Inventario en `productos.csv`, ventas recientes en `ventas.csv`, tarjetas KPI y gráficas con Chart.js |
| 4. Big Data y 24/7 | Generación masiva con NumPy, histórico en `ventas.parquet`, consultas con Polars (parquet + csv en memoria) y corte de caja con APScheduler |

## Cómo funciona la Unidad 4
- `generar_parquet.py` crea 2,000,000 de ventas simuladas con los productos y precios de `productos.csv` y las guarda en `ventas.parquet` (mismas columnas y tipos que `ventas.csv`: `id_venta, fecha, producto, precio, cantidad, monto_total`).
- Al **comprar**, solo se descuenta stock en `productos.csv` y se agrega una fila a `ventas.csv`. El parquet no se reescribe.
- Los endpoints `/api/analisis/*` unen en memoria `ventas.parquet` + `ventas.csv` con `pl.concat()` (sin duplicar datos), así que cada compra se ve al instante en el dashboard.
- Cada 2 minutos (`INTERVALO_CORTE_MINUTOS` en `main.py`) el **corte de caja** (APScheduler, dentro del `lifespan`) fusiona `ventas.csv` en `ventas.parquet` y deja `ventas.csv` solo con encabezados. Todo se hace bajo `async with lock`.

## Librerías
`fastapi`, `uvicorn`, `pandas`, `numpy`, `polars`, `apscheduler` (ver `requirements.txt`).

## Pasos para levantar la aplicación
```bash
pip install -r requirements.txt
python generar_parquet.py      # crea ventas.parquet (solo la primera vez)
uvicorn main:app --reload
```
Después abre `index.html` en el navegador (la API corre en `http://127.0.0.1:8000`).

## Endpoints
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/productos` | Lista el catálogo (`productos.csv`) |
| POST | `/productos` | Agrega un producto |
| DELETE | `/productos/{id}` | Elimina un producto |
| POST | `/productos/{id}` | Compra 1 unidad (stock + fila en `ventas.csv`) |
| GET | `/api/analisis/kpis` | Producto estrella, ingresos totales, transacciones, ticket promedio |
| GET | `/api/analisis/mas-vendidos` | Unidades e ingresos por producto |
| GET | `/api/analisis/ingresos-por-fecha` | Ingresos por día |
