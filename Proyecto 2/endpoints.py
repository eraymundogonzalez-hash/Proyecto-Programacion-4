from fastapi import FastAPI, HTTPException as http_exception
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from pydantic import BaseModel, Field
from typing import List

app = FastAPI(title='Proyecto Tiendita', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

inventario = [
    {"id": 1, "nombre": "Coca-Cola", "precio": 20, "cantidad": 25},
    {"id": 2, "nombre": "Papas", "precio": 15, "cantidad": 40},
    {"id": 3, "nombre": "Café", "precio": 18, "cantidad": 15}
]

#modelo pydantic
class creaProducto(BaseModel):
    nombre: str = Field(..., min_length=2, description="Nombre del producto", example="Coca-Cola")
    precio: float = Field(..., gt=0, description="Precio del producto", example=20.0)
    cantidad: int = Field(..., gt=0, description="Cantidad del producto", example=25)

#la salida de la peticion debe estructurarse de la siguiente manera
class respuestaProducto(BaseModel):
    id: int
    nombre: str
    precio: float
    cantidad: int

# 1. Endpoint convertido a async
@app.get("/")
async def home():
    await asyncio.sleep(0.1)
    return {"Message": "Hola bienvenido"}

# 2. Endpoint convertido a async
@app.get("/productos")
async def getProductos():
    await asyncio.sleep(0.1)
    return inventario

# 3. Endpoint convertido a async
@app.post("/productos", response_model=List[respuestaProducto])
async def addProducto(producto: creaProducto):
    try: 
        await asyncio.sleep(0.1)
        nuevo_id = len(inventario) + 1
        
        # Al usar Pydantic, accedemos a los campos con notación de punto (.) 
        # en lugar de corchetes ([])
        nuevo_producto = {
            "id": nuevo_id,    
            "nombre": producto.nombre,
            "precio": producto.precio,
            "cantidad": producto.cantidad
        }

        inventario.append(nuevo_producto)
        return inventario
    
    except Exception as e:
        return {"Message": f"Error al agregar el producto: {str(e)}"}
    
@app.delete("/productos/{producto_id}")
def deleteProducto(producto_id: int):
    for producto in inventario:
        if producto["id"] == producto_id:
            inventario.remove(producto)
            return {"Message": "El producto fue eliminado"}
    return {"Message": "No fue encontrado el producto"}

#Prueba asyncio
@app.get("/prueba-asyncio")
async def prueba_asyncio():
    print('Comenzando la tarea asincrona')
    await asyncio.sleep(5)
    print('Tarea asincrona finalizada')
    return {"Message": "Hola desde asyncio"}