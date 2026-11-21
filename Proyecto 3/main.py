"""
Título: Proyecto Tiendita
Autor: Edgar González
Fecha de creación: 07/10/2026
Descripción: API para gestión de inventario y ventas con persistencia en CSV y análisis con Pandas
"""

import asyncio
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="API Proyecto Tiendita", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Evita condiciones de carrera al comprar
lock = asyncio.Lock()

# Rutas de los archivos CSV (junto a main.py)
BASE_DIR = Path(__file__).parent
PRODUCTOS_CSV = BASE_DIR / "productos.csv"
VENTAS_CSV = BASE_DIR / "ventas.csv"


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


# Funciones auxiliares para leer/escribir CSV
def leer_productos():
    return pd.read_csv(PRODUCTOS_CSV, encoding="utf-8")


def guardar_productos(df):
    df.to_csv(PRODUCTOS_CSV, index=False, encoding="utf-8")


def leer_ventas():
    return pd.read_csv(VENTAS_CSV, encoding="utf-8")


@app.get("/")
def home():
    return {"Message": "Hola bienvenido"}


# GET - Lista de productos desde productos.csv
@app.get("/productos")
def getProductos():
    return leer_productos().to_dict(orient="records")


# POST - Agrega producto a productos.csv
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


# DELETE - Elimina producto y reescribe productos.csv
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


# POST - Comprar 1 unidad: descuenta stock y registra la venta
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

        # Descontar stock y reescribir productos.csv
        df.at[i, "cantidad"] -= 1
        guardar_productos(df)

        # Registrar la venta en ventas.csv
        precio = float(df.at[i, "precio"])
        venta = pd.DataFrame([{
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "producto_id": int(df.at[i, "id"]),
            "producto": df.at[i, "nombre"],
            "precio": precio,
            "cantidad": 1,
            "total": precio * 1
        }])
        venta.to_csv(VENTAS_CSV, mode="a", header=False, index=False, encoding="utf-8")

        return {"Mensaje": "Producto comprado"}


# ---------- Endpoints analíticos con Pandas ----------

# KPIs para las tarjetas del dashboard
@app.get("/kpis")
def getKpis():
    ventas = leer_ventas()
    if ventas.empty:
        return {
            "producto_estrella": None,
            "unidades_estrella": 0,
            "ingresos_totales": 0,
            "total_transacciones": 0,
            "ticket_promedio": 0
        }

    unidades = ventas.groupby("producto")["cantidad"].sum()
    return {
        "producto_estrella": str(unidades.idxmax()),
        "unidades_estrella": int(unidades.max()),
        "ingresos_totales": float(ventas["total"].sum()),
        "total_transacciones": int(len(ventas)),
        "ticket_promedio": round(float(ventas["total"].mean()), 2)
    }


# Serie 1: unidades e ingresos por producto
@app.get("/ventas/por-producto")
def ventasPorProducto():
    ventas = leer_ventas()
    resumen = (
        ventas.groupby("producto")
        .agg(unidades=("cantidad", "sum"), ingresos=("total", "sum"))
        .reset_index()
        .sort_values("unidades", ascending=False)
    )
    return resumen.to_dict(orient="records")


# Serie 2: ingresos por día
@app.get("/ventas/por-fecha")
def ventasPorFecha():
    ventas = leer_ventas()
    ventas["dia"] = pd.to_datetime(ventas["fecha"]).dt.strftime("%Y-%m-%d")
    resumen = ventas.groupby("dia").agg(ingresos=("total", "sum")).reset_index()
    return resumen.to_dict(orient="records")
