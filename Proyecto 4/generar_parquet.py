"""
Genera ventas.parquet con millones de ventas simuladas
usando los productos y precios reales de productos.csv.

Uso:  python generar_parquet.py
"""

import numpy as np
import polars as pl

N = 2_000_000

# Productos y precios reales de la tienda
productos_df = pl.read_csv("productos.csv")
nombres = productos_df["nombre"].to_numpy()
precios = productos_df["precio"].to_numpy().astype(float)

# Selección aleatoria de productos, cantidades y precios (vectorizado)
indices = np.random.randint(0, len(nombres), N)
prod_elegidos = nombres[indices]
precios_arr = precios[indices]
cantidades = np.random.randint(1, 6, N)

# Fechas aleatorias entre 2026-01-01 y 2026-11-15, ordenadas cronológicamente
inicio = np.datetime64("2026-01-01T00:00:00")
segundos = np.sort(np.random.randint(0, 319 * 86400, N))
fechas = pl.Series((inicio + segundos.astype("timedelta64[s]")).astype("datetime64[us]")).dt.strftime("%Y-%m-%d %H:%M:%S")

# Mismas columnas y tipos que ventas.csv
df = pl.DataFrame({
    "id_venta": np.arange(1, N + 1),
    "fecha": fechas,
    "producto": prod_elegidos,
    "precio": precios_arr,
    "cantidad": cantidades,
    "monto_total": precios_arr * cantidades
}).with_columns(
    pl.col("id_venta").cast(pl.Int64),
    pl.col("cantidad").cast(pl.Int64),
    pl.col("precio").cast(pl.Float64),
    pl.col("monto_total").cast(pl.Float64),
)

df.write_parquet("ventas.parquet")
print(f"ventas.parquet generado con {df.height:,} registros")
print(df.schema)
