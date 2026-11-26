const API_BASE = "http://127.0.0.1:8000";
const API_URL = API_BASE + "/productos";

// Selección de Elementos del DOM
const formProducto = document.getElementById("formProducto");
const tablaProductos = document.getElementById("tablaProductos");
const totalProductos = document.getElementById("totalProductos");

// Instancias de Chart.js (se destruyen antes de volver a dibujar)
let graficaProductos = null;
let graficaFechas = null;


// 1. Función para Cargar Productos (GET)
async function cargarProductos() {
    try {
        const respuesta = await fetch(API_URL);
        const productos = await respuesta.json();

        tablaProductos.innerHTML = "";
        totalProductos.textContent = `${productos.length} productos`;

        // Cada vez que cambia el inventario, se actualiza el dashboard
        cargarDashboard();

        if (productos.length === 0) {
            tablaProductos.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted py-4">
                        No hay productos registrados en la cafetería.
                    </td>
                </tr>`;
            return;
        }

        productos.forEach(p => {
            const fila = document.createElement("tr");
            fila.innerHTML = `
                <td class="fw-bold text-secondary">#${p.id}</td>
                <td>${p.nombre}</td>
                <td class="text-success fw-bold">$${p.precio}</td>
                <td>
                    <span class="badge ${p.cantidad < 10 ? 'bg-danger' : 'bg-success'}">
                        ${p.cantidad} unidades
                    </span>
                </td>
                <td class="text-end">
                    <button class="btn btn-outline-primary btn-sm" onclick="comprarProducto(${p.id})">
                        Comprar
                    </button>
                </td>
                <td class="text-end">
                    <button class="btn btn-outline-danger btn-sm" onclick="eliminarProducto(${p.id})">
                        Eliminar
                    </button>
                </td>
            `;
            tablaProductos.appendChild(fila);
        });

    } catch (error) {
        console.error("Error al cargar productos:", error);
    }
}


// 2. Dashboard: KPIs + gráficas (GET a los endpoints de Pandas)
async function cargarDashboard() {
    try {
        const [kpis, porProducto, porFecha] = await Promise.all([
            fetch(API_BASE + "/api/analisis/kpis").then(r => r.json()),
            fetch(API_BASE + "/api/analisis/mas-vendidos").then(r => r.json()),
            fetch(API_BASE + "/api/analisis/ingresos-por-fecha").then(r => r.json())
        ]);

        // Tarjetas KPI
        document.getElementById("kpiEstrella").textContent =
            kpis.producto_estrella ? `${kpis.producto_estrella} (${kpis.unidades_estrella})` : "-";
        document.getElementById("kpiIngresos").textContent = `$${kpis.ingresos_totales.toLocaleString("es-MX")}`;
        document.getElementById("kpiTransacciones").textContent = kpis.total_transacciones.toLocaleString("es-MX");
        document.getElementById("kpiTicket").textContent = `$${kpis.ticket_promedio}`;

        // Gráfica de barras: unidades por producto
        if (graficaProductos) graficaProductos.destroy();
        graficaProductos = new Chart(document.getElementById("graficaProductos"), {
            type: "bar",
            data: {
                labels: porProducto.map(p => p.producto),
                datasets: [{
                    label: "Unidades vendidas",
                    data: porProducto.map(p => p.unidades),
                    backgroundColor: "#12372f"
                }]
            }
        });

        // Gráfica de líneas: ingresos por día
        if (graficaFechas) graficaFechas.destroy();
        graficaFechas = new Chart(document.getElementById("graficaFechas"), {
            type: "line",
            data: {
                labels: porFecha.map(f => f.dia),
                datasets: [{
                    label: "Ingresos ($)",
                    data: porFecha.map(f => f.ingresos),
                    borderColor: "#f2a541",
                    backgroundColor: "#f2a541",
                    tension: 0.3
                }]
            }
        });

    } catch (error) {
        console.error("Error al cargar el dashboard:", error);
    }
}


async function agregarProducto(event){
    event.preventDefault();

    var nombre = document.getElementById("nombre").value
    var precio = document.getElementById("precio").value
    var cantidad = document.getElementById("cantidad").value

    const nuevoContenido = {nombre, precio, cantidad}
    try {
        const respuesta = await fetch(API_URL, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(nuevoContenido)});

        if(respuesta.ok){
            formProducto.reset();
            await cargarProductos();
        }else{
            console.error("Hubo algo malo al guardar")
        }
    } catch (error) {
        console.log(error)
    }
}

async function eliminarProducto(id_producto){
    try {
        const respuesta = await fetch(API_URL + "/" + id_producto, {method: "DELETE"});

        if(respuesta.ok){
            await cargarProductos();
        }else{
            console.error("Hubo algo malo al eliminar")
        }
    } catch (error) {
        console.log(error)
    }
}

async function comprarProducto(id_producto){
    try {
        const respuesta = await fetch(API_URL + "/" + id_producto, {method: "POST"});

        if(!respuesta.ok){
            const error = await respuesta.json();
            alert(error.detail);
        }
        // Actualiza tabla, KPIs y gráficas
        await cargarProductos();
    } catch (error) {
        console.log(error)
    }
}


// Cargar catálogo y dashboard al abrir la página
document.addEventListener("DOMContentLoaded", cargarProductos);

// Evento para guardar producto
formProducto.addEventListener("submit", agregarProducto);
