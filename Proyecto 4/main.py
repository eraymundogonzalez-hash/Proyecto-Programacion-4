"""
Título: Proyecto Tiendita
Autor: Edgar González
Fecha de creación: 07/10/2026
Descripción: API de inventario y ventas. Productos en CSV, ventas recientes en ventas.csv,
             historial masivo en ventas.parquet (Polars) y corte de caja automático (APScheduler).
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import pandas as pd
import polars as pl
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Evita condiciones de carrera (compras, lecturas del dashboard y corte de caja)
lock = asyncio.Lock()

# Rutas de los archivos
BASE_DIR = Path(__file__).parent
PRODUCTOS_CSV = BASE_DIR / "productos.csv"
VENTAS_CSV = BASE_DIR / "ventas.csv"
VENTAS_PARQUET = BASE_DIR / "ventas.parquet"

# Esquema único de ventas (igual en ventas.csv y ventas.parquet)
ESQUEMA_VENTAS = {
    "id_venta": pl.Int64,
    "fecha": pl.String,
    "producto": pl.String,
    "precio": pl.Float64,
    "cantidad": pl.Int64,
    "monto_total": pl.Float64,
}
ENCABEZADO_VENTAS = ",".join(ESQUEMA_VENTAS) + "\n"

# Corte de caja cada N minutos (para demostración). Para uno diario usar:
# scheduler.add_job(corte_de_caja, "cron", hour=23, minute=59)
INTERVALO_CORTE_MINUTOS = 2

scheduler = AsyncIOScheduler()


# ---------- Corte de caja ----------
def _corte_de_caja_sync():
    recientes = pl.read_csv(VENTAS_CSV, schema=ESQUEMA_VENTAS)
    if recientes.is_empty():
        return 0  # no hay ventas nuevas

    # Fusionar con el histórico y guardar el parquet actualizado
    if VENTAS_PARQUET.exists():
        total = pl.concat([pl.read_parquet(VENTAS_PARQUET), recientes])
    else:
        total = recientes
    temporal = VENTAS_PARQUET.with_suffix(".tmp")
    total.write_parquet(temporal)
    temporal.replace(VENTAS_PARQUET)

    # Vaciar ventas.csv dejando solo los encabezados
    VENTAS_CSV.write_text(ENCABEZADO_VENTAS, encoding="utf-8")
    return recientes.height


async def corte_de_caja():
    async with lock:
        archivadas = await asyncio.to_thread(_corte_de_caja_sync)
    print(f"[Corte de caja] {datetime.now():%H:%M:%S} - ventas archivadas: {archivadas}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(corte_de_caja, "interval", minutes=INTERVALO_CORTE_MINUTOS)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="API Proyecto Tiendita", version="4.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# Modelos de Pydantic
class crearProducto(BaseModel):
    nombre: str = Field(..., min_length=1, description="Nombre del producto")
    precio: float = Field(..., gt=0, description="Precio del producto")
    cantidad: int = Field(..., ge=0, description="stock del producto")


class respuestaProducto(BaseModel):
    id: int
    nombre: str
    precio: float
    cantidad: int


# ---------- Funciones auxiliares ----------
def leer_productos():
    return pd.read_csv(PRODUCTOS_CSV, encoding="utf-8")


def guardar_productos(df):
    df.to_csv(PRODUCTOS_CSV, index=False, encoding="utf-8")


def ventas_completas():
    """Unión virtual: histórico (parquet) + ventas recientes (csv), solo en memoria."""
    recientes = pl.scan_csv(VENTAS_CSV, schema=ESQUEMA_VENTAS)
    if VENTAS_PARQUET.exists():
        return pl.concat([pl.scan_parquet(VENTAS_PARQUET), recientes])
    return recientes


def siguiente_id_venta():
    maximo = ventas_completas().select(pl.col("id_venta").max()).collect().item()
    return int(maximo or 0) + 1


@app.get("/")
def home():
    return {"Message": "Hola bienvenido"}


# ---------- Inventario (CSV) ----------
@app.get("/productos")
def getProductos():
    return leer_productos().to_dict(orient="records")


@app.post("/productos", response_model=respuestaProducto, status_code=status.HTTP_201_CREATED)
def addProducto(producto: crearProducto):
    df = leer_productos()
    nuevo_id = int(df["id"].max()) + 1 if not df.empty else 1
    nuevo = {
        "id": nuevo_id,
        "nombre": producto.nombre,
        "precio": producto.precio,
        "cantidad": producto.cantidad
    }
    df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
    guardar_productos(df)
    return nuevo


@app.delete("/productos/{producto_id}")
def deleteProducto(producto_id: int):
    df = leer_productos()
    if producto_id not in df["id"].values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No fue encontrado el producto"
        )
    df = df[df["id"] != producto_id]
    guardar_productos(df)
    return {"Message": "El producto fue eliminado"}


# ---------- Compra: descuenta stock y agrega UNA fila a ventas.csv ----------
@app.post("/productos/{producto_id}")
async def comprarProducto(producto_id: int):
    async with lock:
        df = leer_productos()
        filas = df.index[df["id"] == producto_id]

        if len(filas) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe el ID de ese producto"
            )

        i = filas[0]
        if df.at[i, "cantidad"] <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay stock de ese producto"
            )

        df.at[i, "cantidad"] -= 1
        guardar_productos(df)

        precio = float(df.at[i, "precio"])
        venta = pd.DataFrame([{
            "id_venta": siguiente_id_venta(),
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "producto": df.at[i, "nombre"],
            "precio": precio,
            "cantidad": 1,
            "monto_total": precio * 1
        }])
        venta.to_csv(VENTAS_CSV, mode="a", header=False, index=False, encoding="utf-8")

        return {"Mensaje": "Producto comprado"}


# ---------- Endpoints analíticos con Polars (parquet + csv) ----------
# Se consultan bajo el lock para no leer a la mitad de un corte de caja (evita duplicados).

def _kpis():
    ventas = ventas_completas()
    resumen = ventas.select(
        pl.col("monto_total").sum().alias("ingresos_totales"),
        pl.len().alias("total_transacciones"),
        pl.col("monto_total").mean().alias("ticket_promedio"),
    ).collect().to_dicts()[0]

    estrella = (
        ventas.group_by("producto")
        .agg(pl.col("cantidad").sum().alias("unidades"))
        .sort("unidades", descending=True)
        .head(1)
        .collect()
        .to_dicts()
    )

    return {
        "producto_estrella": estrella[0]["producto"] if estrella else None,
        "unidades_estrella": int(estrella[0]["unidades"]) if estrella else 0,
        "ingresos_totales": round(resumen["ingresos_totales"] or 0, 2),
        "total_transacciones": int(resumen["total_transacciones"]),
        "ticket_promedio": round(resumen["ticket_promedio"] or 0, 2),
    }


def _mas_vendidos():
    return (
        ventas_completas()
        .group_by("producto")
        .agg(
            pl.col("cantidad").sum().alias("unidades"),
            pl.col("monto_total").sum().round(2).alias("ingresos"),
        )
        .sort("unidades", descending=True)
        .collect()
        .to_dicts()
    )


def _ingresos_por_fecha():
    return (
        ventas_completas()
        .with_columns(pl.col("fecha").str.slice(0, 10).alias("dia"))
        .group_by("dia")
        .agg(pl.col("monto_total").sum().round(2).alias("ingresos"))
        .sort("dia")
        .collect()
        .to_dicts()
    )


@app.get("/api/analisis/kpis")
async def getKpis():
    async with lock:
        return await asyncio.to_thread(_kpis)


@app.get("/api/analisis/mas-vendidos")
async def getMasVendidos():
    async with lock:
        return await asyncio.to_thread(_mas_vendidos)


@app.get("/api/analisis/ingresos-por-fecha")
async def getIngresosPorFecha():
    async with lock:
        return await asyncio.to_thread(_ingresos_por_fecha)
