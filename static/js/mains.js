// ==========================================
// MODAL DE MOVIMIENTOS E INVENTARIO
// ==========================================
function abrirModalMovimiento(id, nombre) {
    document.getElementById('mov-producto-id').value = id;
    document.getElementById('mov-producto-nombre').innerText = nombre;
    actualizarCamposMovimiento();
    const modal = document.getElementById('modal-movimiento');
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
}

function cerrarModalMovimiento() {
    const modal = document.getElementById('modal-movimiento');
    if (modal) {
        modal.classList.remove('flex');
        modal.classList.add('hidden');
    }
}

function actualizarCamposMovimiento() {
    const opSelect = document.getElementById('tipo_operacion');
    if (!opSelect) return;

    const op = opSelect.value;
    const selectConcepto = document.getElementById('concepto');
    const blockOrigen = document.getElementById('block-origen');
    const blockDestino = document.getElementById('block-destino');

    if (!selectConcepto) return;

    selectConcepto.innerHTML = '';

    if (op === 'traslado') {
        selectConcepto.innerHTML = '<option value="Traslado Interno">Traslado entre Áreas</option>';
        if (blockOrigen) blockOrigen.classList.remove('hidden');
        if (blockDestino) blockDestino.classList.remove('hidden');
    } else if (op === 'entrada') {
        selectConcepto.innerHTML = `
            <option value="Compra / Reposición">Compra / Reposición</option>
            <option value="Ajuste Positivo">Ajuste de Inventario (+)</option>
            <option value="Devolución">Devolución de Cliente</option>
        `;
        if (blockOrigen) blockOrigen.classList.add('hidden');
        if (blockDestino) blockDestino.classList.remove('hidden');
    } else if (op === 'salida') {
        selectConcepto.innerHTML = `
            <option value="Venta Directa">Venta Directa</option>
            <option value="Merma / Deterioro">Merma / Deterioro</option>
            <option value="Autoconsumo">Autoconsumo / Uso Interno</option>
            <option value="Ajuste Negativo">Ajuste de Inventario (-)</option>
        `;
        if (blockOrigen) blockOrigen.classList.remove('hidden');
        if (blockDestino) blockDestino.classList.add('hidden');
    }
}


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

    if (filas.length === 0) return;

    filas.forEach(row => {
        let precio = parseFloat(row.dataset.precio) || 0;
        let inicial = parseFloat(row.querySelector('.stock-inicial')?.value) || 0;
        let entradas = parseFloat(row.querySelector('.entradas')?.value) || 0;
        let final = parseFloat(row.querySelector('.stock-final')?.value) || 0;

        let vendidos = (inicial + entradas) - final;
        if (vendidos < 0) vendidos = 0;

        let subtotal = vendidos * precio;
        totalEsperado += subtotal;

        const elVendidos = row.querySelector('.vendidos');
        const elSubtotal = row.querySelector('.subtotal');

        if (elVendidos) elVendidos.textContent = vendidos.toFixed(2);
        if (elSubtotal) elSubtotal.textContent = '$' + subtotal.toFixed(2);
    });

    const elTotalEsperado = document.getElementById('total-esperado');
    const elDineroCaja = document.getElementById('dinero-caja');
    const btnCierre = document.getElementById('btn-cierre');

    if (elTotalEsperado) {
        elTotalEsperado.textContent = '$' + totalEsperado.toFixed(2);
    }

    if (elDineroCaja && btnCierre) {
        let valorCajaRaw = elDineroCaja.value.trim();
        let efectivoFisico = parseFloat(valorCajaRaw);

        // 1. Calculamos la diferencia entre el efectivo ingresado y el total esperado
        let diferencia = Math.abs(efectivoFisico - totalEsperado);

        // 2. La caja cuadra solo si la diferencia es 0 (usamos < 0.01 por decimales en JS) 
        // y se ingresó un valor válido
        let cajaCuadrada = valorCajaRaw !== '' && !isNaN(efectivoFisico) && diferencia < 0.01;

        if (cajaCuadrada) {
            btnCierre.disabled = false;
            btnCierre.className = "w-full md:w-auto px-8 py-3.5 bg-orange-600 hover:bg-orange-500 text-white font-bold rounded-xl cursor-pointer transition-all duration-200 flex items-center justify-center gap-2 shadow-lg shadow-orange-600/30 active:scale-95";
        } else {
            btnCierre.disabled = true;
            btnCierre.className = "w-full md:w-auto px-8 py-3.5 bg-gray-800 text-gray-500 font-bold rounded-xl cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2 shadow-lg";
        }
    }
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
// INICIALIZACIÓN DE EVENTOS AL CARGAR EL DOM
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    // 1. Sugerencia de margen +30% en creación de producto
    const inputCosto = document.getElementById('precio_costo');
    const inputVenta = document.getElementById('precio_venta');
    const textoSugerencia = document.getElementById('sugerencia_texto');

    if (inputCosto && inputVenta) {
        inputCosto.addEventListener('input', () => {
            const costo = parseFloat(inputCosto.value) || 0;

            if (costo > 0) {
                const sugerido = (costo * 1.30).toFixed(2);
                inputVenta.value = sugerido;

                if (textoSugerencia) {
                    textoSugerencia.textContent = `Sugerido (+30%): $${sugerido}`;
                }
            } else {
                inputVenta.value = '';
                if (textoSugerencia) {
                    textoSugerencia.textContent = '';
                }
            }
        });
    }

    // 2. Escuchador para el buscador tipo píldora de cierre.html
    const inputBuscador = document.getElementById('buscador');
    if (inputBuscador) {
        inputBuscador.addEventListener('keyup', filtrarProductos);
    }

    // 3. Ejecutar cálculo inicial si estamos en la vista de cierre
    calcular();
});
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