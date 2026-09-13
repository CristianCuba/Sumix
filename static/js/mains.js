
// ==========================================
// MODAL DE PRODUCTOS
// ==========================================
function abrirModalProducto() {
    const modal = document.getElementById('modal-producto');
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
}

function cerrarModalProducto() {
    const modal = document.getElementById('modal-producto');
    if (modal) {
        modal.classList.remove('flex');
        modal.classList.add('hidden');
    }
}

// ==========================================
// MODAL DE EDICIÓN DE PRODUCTOS
// ==========================================
function abrirModalEditarProducto(btn) {
    // 1. Obtener los atributos data- del botón
    const id = btn.getAttribute('data-id');
    const nombre = btn.getAttribute('data-nombre');
    const unidad = btn.getAttribute('data-unidad');
    const costo = btn.getAttribute('data-costo');
    const venta = btn.getAttribute('data-venta');
    const proveedorId = btn.getAttribute('data-proveedor');
    const fechaVenc = btn.getAttribute('data-vencimiento');

    const modal = document.getElementById('modal-editar-producto');
    const form = document.getElementById('form-editar-producto');

    if (modal && form) {
        // Asignar el endpoint de actualización con el ID del producto
        form.action = `/editar_producto/${id}`;

        // Rellenar cada campo del formulario
        if (document.getElementById('edit_nombre')) document.getElementById('edit_nombre').value = nombre || '';
        if (document.getElementById('edit_unidad_medida')) document.getElementById('edit_unidad_medida').value = unidad || 'u';
        if (document.getElementById('edit_precio_costo')) document.getElementById('edit_precio_costo').value = costo || '0';
        if (document.getElementById('edit_precio_venta')) document.getElementById('edit_precio_venta').value = venta || '0';
        if (document.getElementById('edit_proveedor_id')) document.getElementById('edit_proveedor_id').value = proveedorId || '';
        if (document.getElementById('edit_fecha_vencimiento')) document.getElementById('edit_fecha_vencimiento').value = fechaVenc || '';

        // Mostrar el modal
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
}

function cerrarModalEditarProducto() {
    const modal = document.getElementById('modal-editar-producto');
    if (modal) {
        modal.classList.remove('flex');
        modal.classList.add('hidden');
    }
}

function cerrarModalEditarProducto() {
    const modal = document.getElementById('modal-editar-producto');
    if (modal) {
        modal.classList.remove('flex');
        modal.classList.add('hidden');
    }
}
function filtrarTablaProductos() {
    const input = document.getElementById('filtro-productos');
    const filter = input.value.toLowerCase().trim();
    
    // Selecciona todas las filas dentro del tbody de la tabla
    const filas = document.querySelectorAll('tbody tr');

    filas.forEach(fila => {
        // Obtiene todo el texto visible de la fila (nombre, proveedor, etc.)
        const textoFila = fila.textContent.toLowerCase();

        // Oculta o muestra la fila según coincida con la búsqueda
        if (textoFila.includes(filter)) {
            fila.style.display = '';
        } else {
            fila.style.display = 'none';
        }
    });
}


// Declaraciones al inicio (solo una vez)
var mapaStock = {};
var productoSeleccionadoId = null;

function cargarMapaStock(datosStock) {
    mapaStock = datosStock || {};
}

function abrirModalTraslado(id, nombre) {
    productoSeleccionadoId = id;

    const campoId = document.getElementById('modalProductoId');
    const campoNombre = document.getElementById('modalProductoNombre');
    const modal = document.getElementById('modalTraslado');
    const selectorOrigen = document.getElementById('modalAlmacenOrigen');

    if (campoId) campoId.value = id;
    if (campoNombre) campoNombre.textContent = 'Producto: ' + nombre;
    if (modal) modal.classList.remove('hidden');

    // Inicializar selectores de conceptos y comportamiento
    if (typeof actualizarConceptos === 'function') actualizarConceptos();
    if (typeof cambiarTipoOperacion === 'function') cambiarTipoOperacion();

    // AUTO-SELECCIONAR el almacén que tenga stock disponible para evitar enviar un ID incorrecto
    if (selectorOrigen && window.mapaStock && window.mapaStock[productoSeleccionadoId]) {
        const stockProducto = window.mapaStock[productoSeleccionadoId];
        // Buscar el primer almacén con stock > 0
        const almacenConStock = Object.keys(stockProducto).find(almId => stockProducto[almId] > 0);
        
        if (almacenConStock) {
            selectorOrigen.value = almacenConStock;
        }
    }

    if (typeof actualizarStockDisponible === 'function') {
        actualizarStockDisponible();
    }
}

function actualizarConceptos() {
    const selectTipo = document.getElementById('modalTipoOperacion');
    const selectConcepto = document.getElementById('modalConcepto');
    if (!selectTipo || !selectConcepto) return;

    const tipoIdActual = parseInt(selectTipo.value);
    selectConcepto.innerHTML = '';

    const filtrados = listaConceptos.filter(c => c.tipo_id === tipoIdActual);
    
    if (filtrados.length === 0) {
        let opt = document.createElement('option');
        opt.value = "";
        opt.textContent = "No hay conceptos para este tipo";
        selectConcepto.appendChild(opt);
    } else {
        filtrados.forEach(c => {
            let opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.nombre;
            selectConcepto.appendChild(opt);
        });
    }
}

function cambiarTipoOperacion() {
    if (typeof actualizarConceptos === 'function') {
        actualizarConceptos(); 
    }

    const selectTipo = document.getElementById('modalTipoOperacion');
    if (!selectTipo) return;

    const selectedOption = selectTipo.options[selectTipo.selectedIndex];
    
    // Leemos los atributos booleanos que definiste en la base de datos
    const requiereOrigen = selectedOption.getAttribute('data-requiere-origen') === 'true';
    const requiereDestino = selectedOption.getAttribute('data-requiere-destino') === 'true';

    const contenedorOrigen = document.getElementById('contenedorOrigen');
    const contenedorDestino = document.getElementById('contenedorDestino');
    const inputOrigen = document.getElementById('modalAlmacenOrigen');
    const inputDestino = document.getElementById('modalAlmacenDestino');

    if (!contenedorOrigen || !contenedorDestino) return;

    // Manejo dinámico del Origen
    if (requiereOrigen) {
        contenedorOrigen.style.display = 'block';
        if (inputOrigen) inputOrigen.required = true;
        if (typeof actualizarStockDisponible === 'function') actualizarStockDisponible();
    } else {
        contenedorOrigen.style.display = 'none';
        if (inputOrigen) inputOrigen.required = false;
    }

    // Manejo dinámico del Destino
    if (requiereDestino) {
        contenedorDestino.style.display = 'block';
        if (inputDestino) inputDestino.required = true;
    } else {
        contenedorDestino.style.display = 'none';
        if (inputDestino) inputDestino.required = false;
    }
}

function actualizarStockDisponible() {
    if (!productoSeleccionadoId) return;

    const selectorOrigen = document.getElementById('modalAlmacenOrigen');
    const textoStock = document.getElementById('stockDisponibleText');

    if (!selectorOrigen || !textoStock) return;

    const almacenId = selectorOrigen.value;
    const stockProducto = (window.mapaStock && window.mapaStock[productoSeleccionadoId]) || {};
    const cantidadDisponible = stockProducto[almacenId] ?? stockProducto[parseInt(almacenId)] ?? 0;

    textoStock.textContent = `Disponible: ${cantidadDisponible}`;
    textoStock.className = cantidadDisponible <= 0 
        ? "text-xs font-mono font-bold text-rose-500" 
        : "text-xs font-mono font-bold text-emerald-400";
}

function cerrarModalTraslado() {
    const modal = document.getElementById('modalTraslado');
    if (modal) modal.classList.add('hidden');
    productoSeleccionadoId = null;
}

function actualizarStockDisponible() {
    if (!productoSeleccionadoId) return;

    const selectorOrigen = document.getElementById('modalAlmacenOrigen');
    const textoStock = document.getElementById('stockDisponibleText');

    if (!selectorOrigen || !textoStock) return;

    const almacenId = selectorOrigen.value;
    
    // Aseguramos conversión de tipos por si las claves del objeto son numéricas y el value es string
    const stockProducto = mapaStock[productoSeleccionadoId] || {};
    const cantidadDisponible = stockProducto[almacenId] ?? stockProducto[parseInt(almacenId)] ?? 0;

    textoStock.textContent = `Disponible: ${cantidadDisponible}`;

    if (cantidadDisponible <= 0) {
        textoStock.className = "text-xs font-mono font-bold text-rose-500";
    } else {
        textoStock.className = "text-xs font-mono font-bold text-emerald-400";
    }
}


// ==========================================
// CONTROL DEL CIERRE DE DÍA Y ARQUEO DE CAJA
// ==========================================

// Búsqueda / Filtrado dinámico de productos en la tabla de cierre
function filtrarProductos() {
    const inputBuscador = document.getElementById('buscador');
    if (!inputBuscador) return;

    const query = inputBuscador.value.toLowerCase();
    const filas = document.querySelectorAll('.fila-producto');

    filas.forEach(fila => {
        const celdaNombre = fila.querySelector('.nombre-prod') || fila.cells[0];
        const nombre = celdaNombre ? celdaNombre.textContent.toLowerCase() : '';
        fila.style.display = nombre.includes(query) ? '' : 'none';
    });
}

// Recálculo dinámico de ventas, subtotales y habilitación del botón de cierre
function calcular() {
    let totalEsperado = 0;
    const filas = document.querySelectorAll('.fila-producto');

    filas.forEach(fila => {
        const idProducto = fila.getAttribute('data-id');
        const precio = parseFloat(fila.getAttribute('data-precio')) || 0;
        
        const inputInicial = fila.querySelector('.stock-inicial');
        const inputEntradas = fila.querySelector('.entradas');
        const inputFinal = fila.querySelector('.stock-final');
        const spanVendidos = fila.querySelector('.vendidos');
        const spanSubtotal = fila.querySelector('.subtotal');

        const inicial = parseFloat(inputInicial.value) || 0;
        const entradas = parseFloat(inputEntradas.value) || 0;
        const finalFisico = parseFloat(inputFinal.value) || 0;

        // 1. Calcular cuánto se comió/sacó por deudas/apuntes para este producto específico
        let cantidadEnDeudas = 0;
        if (typeof listaDeudas !== 'undefined') {
            listaDeudas.forEach(deuda => {
                if (deuda.productoId === idProducto) {
                    cantidadEnDeudas += deuda.cantidad;
                }
            });
        }

        // 2. Vendidos reales = Lo que falta en inventario MENOS lo que se registró como deuda/retiro
        let vendidosBrutos = (inicial + entradas) - finalFisico;
        let vendidosReales = vendidosBrutos - cantidadEnDeudas;
        
        // Evitar números negativos por seguridad visual
        if (vendidosReales < 0) vendidosReales = 0;

        const subtotal = vendidosReales * precio;

        // Actualizar la interfaz de la fila
        spanVendidos.textContent = vendidosReales.toFixed(vendidosReales % 1 !== 0 ? 2 : 0);
        spanSubtotal.textContent = `$${subtotal.toFixed(2)}`;

        totalEsperado += subtotal;
    });

    // Actualizar el total esperado abajo en la barra de cierre
    const spanTotalEsperado = document.getElementById('total-esperado');
    if (spanTotalEsperado) {
        spanTotalEsperado.textContent = `$${totalEsperado.toFixed(2)}`;
    }

    // Validar si se puede cerrar caja (ejemplo de validación de botones)
    validarCierreCaja(totalEsperado);
}
let listaDeudas = [];

    function agregarDeuda() {
        const selectProd = document.getElementById('deuda-producto-select');
        const opcionSelected = selectProd.options[selectProd.selectedIndex];

        const productoId = selectProd.value;
        const productoNombre = opcionSelected.getAttribute('data-nombre');
        const precioVenta = parseFloat(opcionSelected.getAttribute('data-precio')) || 0;

        const conceptoInput = document.getElementById('deuda-concepto');
        const concepto = conceptoInput.value.trim() || "Consumo Personal / Dueño";

        const cantidadInput = document.getElementById('deuda-cantidad');
        const cantidad = parseFloat(cantidadInput.value) || 0;

        if (cantidad <= 0) {
            alert("La cantidad debe ser mayor a 0");
            return;
        }

        // Añadir al array temporal
        listaDeudas.push({
            id: Date.now(),
            productoId: productoId,
            productoNombre: productoNombre,
            concepto: concepto,
            cantidad: cantidad,
            subtotal: cantidad * precioVenta
        });

        // Limpiar inputs de deudas
        conceptoInput.value = "";
        cantidadInput.value = "1";

        renderizarDeudas();
        calcular();
    }

    function eliminarDeuda(id) {
        listaDeudas = listaDeudas.filter(item => item.id !== id);
        renderizarDeudas();
        calcular();
    }

    function renderizarDeudas() {
        const container = document.getElementById('tabla-deudas-container');

        if (listaDeudas.length === 0) {
            container.innerHTML = `<tr id="sin-deudas-row"><td colspan="5" class="py-4 text-center text-gray-500 italic">No hay apuntes o deudas registradas en este turno.</td></tr>`;
            return;
        }

        let html = '';
        listaDeudas.forEach(item => {
            html += `
                <tr class="hover:bg-gray-800/20">
                    <td class="py-2.5 px-3 font-medium text-white">${item.concepto}</td>
                    <td class="py-2.5 px-3 text-gray-300">${item.productoNombre}</td>
                    <td class="py-2.5 px-3 text-center font-mono text-orange-400">${item.cantidad}</td>
                    <td class="py-2.5 px-3 text-right font-mono text-white">$${item.subtotal.toFixed(2)}</td>
                    <td class="py-2.5 px-3 text-center">
                        <button type="button" onclick="eliminarDeuda(${item.id})" class="text-rose-400 hover:text-rose-300 font-bold px-2 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 transition">Quitar</button>
                    </td>
                </tr>
            `;
        });
        container.innerHTML = html;
    }
// Envío de la liquidación del cierre al backend vía fetch()
async function enviarCierre() {
    const elDineroCaja = document.getElementById('dinero-caja');
    const efectivoCaja = parseFloat(elDineroCaja ? elDineroCaja.value : 0) || 0;

    if (!confirm("¿Estás seguro de efectuar el cierre del día? Esto guardará el reporte y actualizará el inventario actual.")) {
        return;
    }

    const productos = [];
    const filas = document.querySelectorAll('.fila-producto');

    filas.forEach(fila => {
        const id = fila.dataset.id;
        const inicial = parseFloat(fila.querySelector('.stock-inicial')?.value) || 0;
        const entradas = parseFloat(fila.querySelector('.entradas')?.value) || 0;
        const final = parseFloat(fila.querySelector('.stock-final')?.value) || 0;
        const vendidos = parseFloat(fila.querySelector('.vendidos')?.textContent) || 0;
        
        let subtotalTexto = fila.querySelector('.subtotal')?.textContent || '0';
        const subtotal = parseFloat(subtotalTexto.replace('$', '')) || 0;

        if (id) {
            productos.push({
                id: id,
                stock_inicial: inicial,
                entradas: entradas,
                stock_final: final,
                vendidos: vendidos,
                subtotal: subtotal
            });
        }
    });

    const btnCierre = document.getElementById('btn-cierre');
    if (btnCierre) btnCierre.disabled = true;

    try {
        const response = await fetch('/procesar_cierre', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                efectivo_caja: efectivoCaja,
                productos: productos
            })
        });

        const res = await response.json();
        if (res.success) {
            alert(res.message);
            window.location.reload();
        } else {
            alert("Error al procesar el cierre: " + res.message);
            if (btnCierre) btnCierre.disabled = false;
        }
    } catch (err) {
        alert("Ocurrió un error de conexión al enviar el cierre.");
        console.error("Error en enviarCierre:", err);
        if (btnCierre) btnCierre.disabled = false;
    }
}


// ==========================================
// CONSULTA Y MODAL DE DETALLE DE CIERRE
// ==========================================
async function verDetalleCierre(idCierre) {
    try {
        const response = await fetch(`/admin/cierres/${idCierre}/detalle`);
        const res = await response.json();

        if (!res.success) {
            alert(res.message);
            return;
        }

        const cierre = res.cierre;
        const detalles = res.detalles;

        // Cargar encabezados
        document.getElementById('modal-cierre-titulo').textContent = `Detalle del Cierre #${cierre.id}`;
        document.getElementById('modal-cierre-subtitulo').textContent = `Fecha: ${cierre.fecha} | Responsable: ${cierre.usuario_nombre}`;
        document.getElementById('modal-total-esperado').textContent = `$${cierre.total_esperado.toFixed(2)}`;
        document.getElementById('modal-efectivo-caja').textContent = `$${cierre.efectivo_caja.toFixed(2)}`;

        const elDif = document.getElementById('modal-diferencia');
        if (cierre.diferencia < 0) {
            elDif.textContent = `-$${Math.abs(cierre.diferencia).toFixed(2)}`;
            elDif.className = "text-xl font-bold font-mono text-red-400";
        } else if (cierre.diferencia > 0) {
            elDif.textContent = `+$${cierre.diferencia.toFixed(2)}`;
            elDif.className = "text-xl font-bold font-mono text-blue-400";
        } else {
            elDif.textContent = "$0.00";
            elDif.className = "text-xl font-bold font-mono text-gray-400";
        }

        // Llenar tabla de productos
        const tbody = document.getElementById('modal-tabla-detalles');
        tbody.innerHTML = '';

        detalles.forEach(d => {
            const tr = document.createElement('tr');
            tr.className = "hover:bg-gray-800/30 transition-colors";
            tr.innerHTML = `
                <td class="p-3 text-white font-medium">${d.nombre_producto}</td>
                <td class="p-3 text-gray-300">$${d.precio_venta.toFixed(2)}</td>
                <td class="p-3 text-gray-400 font-mono">${d.stock_inicial}</td>
                <td class="p-3 text-gray-400 font-mono">${d.entradas}</td>
                <td class="p-3 text-orange-400 font-bold font-mono">${d.stock_final}</td>
                <td class="p-3 text-white font-bold font-mono">${d.vendidos}</td>
                <td class="p-3 text-right font-bold font-mono text-white">$${d.subtotal.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        });

        // Abrir Modal
        const modal = document.getElementById('modal-detalle-cierre');
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
        }

    } catch (err) {
        console.error("Error consultando el detalle del cierre:", err);
        alert("Ocurrió un error al obtener el detalle del cierre.");
    }
}

function cerrarModalDetalleCierre() {
    const modal = document.getElementById('modal-detalle-cierre');
    if (modal) {
        modal.classList.remove('flex');
        modal.classList.add('hidden');
    }
}


// ==========================================
// UTILIDADES
// ==========================================
function actualizarNombreArchivo(input) {
    const label = document.getElementById('file-label-text');
    if (input.files && input.files[0]) {
        label.textContent = input.files[0].name;
    } else {
        label.textContent = "Seleccionar archivo .db";
    }
}
function calcularSugerenciaVenta() {
    const inputCosto = document.getElementById('precio_costo');
    const inputVenta = document.getElementById('precio_venta');
    const textoSugerencia = document.getElementById('sugerencia_texto');

    if (!inputCosto || !inputVenta) return;

    const costo = parseFloat(inputCosto.value) || 0;

    if (costo > 0) {
        const sugerido = (costo * 1.30).toFixed(2);
        
        // Asigna la sugerencia si el campo de venta está vacío o es 0
        if (!inputVenta.value || parseFloat(inputVenta.value) === 0) {
            inputVenta.value = sugerido;
        }

        if (textoSugerencia) {
            textoSugerencia.textContent = `Sugerido (+30%): $${sugerido}`;
        }
    } else {
        if (textoSugerencia) {
            textoSugerencia.textContent = '';
        }
    }
}

// ==========================================
// INICIALIZACIÓN DE EVENTOS AL CARGAR EL DOM
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
       // 2. Escuchador para el buscador de productos en cierre
    const inputBuscador = document.getElementById('buscador');
    if (inputBuscador) {
        inputBuscador.addEventListener('keyup', filtrarProductos);
    }

    // 3. Ejecutar cálculo inicial si estamos en la vista de cierre
    calcular();
});