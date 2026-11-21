# Cafetería Brisa – Tiendita Full-Stack (Programación IV, Proyecto 3)

Tienda web con FastAPI, persistencia en CSV, análisis con Pandas y dashboard con Chart.js.

## Estructura
- `main.py` – API FastAPI (CRUD de productos, compras, KPIs y series con Pandas)
- `productos.csv` – catálogo e inventario
- `ventas.csv` – historial de compras
- `index.html` / `app.js` – interfaz, tarjetas KPI y gráficas Chart.js

## Cómo ejecutarlo
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
Después abre `index.html` en el navegador (la API corre en `http://127.0.0.1:8000`).

## Endpoints
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/productos` | Lista productos desde `productos.csv` |
| POST | `/productos` | Agrega un producto |
| POST | `/productos/{id}` | Compra 1 unidad (descuenta stock y registra en `ventas.csv`) |
| DELETE | `/productos/{id}` | Elimina el producto y reescribe el CSV |
| GET | `/kpis` | Producto estrella, ingresos totales, transacciones y ticket promedio |
| GET | `/ventas/por-producto` | Unidades e ingresos por producto |
| GET | `/ventas/por-fecha` | Ingresos por día |
