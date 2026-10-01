// ==========================================
// VARIABLES GLOBALES
// ==========================================
var mapaStock = {};
var productoSeleccionadoId = null;

// ==========================================
// MODAL DE PRODUCTOS (CREACIÓN / EDICIÓN)
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

function abrirModalEditarProducto(btn) {
    const id = btn.getAttribute('data-id');
    const nombre = btn.getAttribute('data-nombre');
    const unidad = btn.getAttribute('data-unidad');
    const costo = btn.getAttribute('data-costo');
    const venta = btn.getAttribute('data-venta');
    const proveedorId = btn.getAttribute('data-proveedor');
    const propietarioId = btn.getAttribute('data-propietario');
    const fechaVenc = btn.getAttribute('data-vencimiento');

    const modal = document.getElementById('modal-editar-producto');
    const form = document.getElementById('form-editar-producto');

    if (modal && form) {
        form.action = `/editar_producto/${id}`;

        if (document.getElementById('edit_nombre')) document.getElementById('edit_nombre').value = nombre || '';
        if (document.getElementById('edit_unidad_medida')) document.getElementById('edit_unidad_medida').value = unidad || 'u';
        if (document.getElementById('edit_precio_costo')) document.getElementById('edit_precio_costo').value = costo || '0';
        if (document.getElementById('edit_precio_venta')) document.getElementById('edit_precio_venta').value = venta || '0';
        if (document.getElementById('edit_proveedor_id')) document.getElementById('edit_proveedor_id').value = proveedorId || '';
        if (document.getElementById('edit_propietario_id')) document.getElementById('edit_propietario_id').value = propietarioId || '';
        if (document.getElementById('edit_fecha_vencimiento')) document.getElementById('edit_fecha_vencimiento').value = fechaVenc || '';

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

function filtrarTablaProductos() {
    const input = document.getElementById('filtro-productos');
    if (!input) return;
    const filter = input.value.toLowerCase().trim();
    const filas = document.querySelectorAll('tbody tr');

    filas.forEach(fila => {
        const textoFila = fila.textContent.toLowerCase();
        fila.style.display = textoFila.includes(filter) ? '' : 'none';
    });
}

// ==========================================
// MODAL Y MOVIMIENTOS DE TRASLADO DE STOCK
// ==========================================
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

    if (typeof actualizarConceptos === 'function') actualizarConceptos();
    if (typeof cambiarTipoOperacion === 'function') cambiarTipoOperacion();

    if (selectorOrigen && mapaStock && mapaStock[productoSeleccionadoId]) {
        const stockProducto = mapaStock[productoSeleccionadoId];
        const almacenConStock = Object.keys(stockProducto).find(almId => stockProducto[almId] > 0);
        if (almacenConStock) {
            selectorOrigen.value = almacenConStock;
        }
    }

    actualizarStockDisponible();
}

function actualizarConceptos() {
    const selectTipo = document.getElementById('modalTipoOperacion');
    const selectConcepto = document.getElementById('modalConcepto');
    if (!selectTipo || !selectConcepto || typeof listaConceptos === 'undefined') return;

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
    actualizarConceptos();

    const selectTipo = document.getElementById('modalTipoOperacion');
    if (!selectTipo) return;

    const selectedOption = selectTipo.options[selectTipo.selectedIndex];
    const requiereOrigen = selectedOption.getAttribute('data-requiere-origen') === 'true';
    const requiereDestino = selectedOption.getAttribute('data-requiere-destino') === 'true';

    const contenedorOrigen = document.getElementById('contenedorOrigen');
    const contenedorDestino = document.getElementById('contenedorDestino');
    const inputOrigen = document.getElementById('modalAlmacenOrigen');
    const inputDestino = document.getElementById('modalAlmacenDestino');

    if (!contenedorOrigen || !contenedorDestino) return;

    if (requiereOrigen) {
        contenedorOrigen.style.display = 'block';
        if (inputOrigen) inputOrigen.required = true;
        actualizarStockDisponible();
    } else {
        contenedorOrigen.style.display = 'none';
        if (inputOrigen) inputOrigen.required = false;
    }

    if (requiereDestino) {
        contenedorDestino.style.display = 'block';
        if (inputDestino) inputDestino.required = true;
    } else {
        contenedorDestino.style.display = 'none';
        if (inputDestino) inputDestino.required = false;
    }
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
    const stockProducto = mapaStock[productoSeleccionadoId] || {};
    const cantidadDisponible = stockProducto[almacenId] ?? stockProducto[parseInt(almacenId)] ?? 0;

    textoStock.textContent = `Disponible: ${cantidadDisponible}`;
    textoStock.className = cantidadDisponible <= 0
        ? "text-xs font-mono font-bold text-rose-500"
        : "text-xs font-mono font-bold text-emerald-400";
}

// ==========================================
// CONTROL DE CIERRE DE DÍA Y ARQUEO DE CAJA
// ==========================================
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

function calcular() {
    let totalBrutoGeneral = 0;
    let ventasDayana = 0;
    let tieneCristian = false;

    const filas = document.querySelectorAll('.fila-producto');

    filas.forEach(fila => {
        const precioAttr = fila.getAttribute('data-precio') || "0";
        const precio = parseFloat(precioAttr.replace(',', '.')) || 0;

        const inputInicial = fila.querySelector('.stock-inicial');
        const inputEntradas = fila.querySelector('.entradas');
        const inputFinal = fila.querySelector('.stock-final');

        const stockInicial = inputInicial ? (parseFloat(inputInicial.value) || 0) : 0;
        const entradas = inputEntradas ? (parseFloat(inputEntradas.value) || 0) : 0;
        const stockFinal = inputFinal ? (parseFloat(inputFinal.value) || 0) : 0;

        let vendidos = (stockInicial + entradas) - stockFinal;

        const spanVendidos = fila.querySelector('.vendidos');
        const spanSubtotal = fila.querySelector('.subtotal');

        if (vendidos < 0) {
            vendidos = 0;
            if (spanVendidos) {
                spanVendidos.textContent = "Exceso físico";
                spanVendidos.className = "p-4 font-bold text-amber-400 font-mono vendidos text-xs";
            }
        } else {
            if (spanVendidos) {
                spanVendidos.textContent = vendidos;
                spanVendidos.className = "p-4 font-bold text-white font-mono vendidos";
            }
        }

        const subtotal = vendidos * precio;
        totalBrutoGeneral += subtotal;

        const propId = parseInt(fila.getAttribute('data-propietario-id')) || 0;
        const propNombre = (fila.getAttribute('data-propietario-nombre') || "").toLowerCase();

        if (vendidos > 0) {
            if (propId === 1 || propNombre.includes('dayana')) {
                ventasDayana += subtotal;
            }
            if (propId === 2 || propNombre.includes('cristian')) {
                tieneCristian = true;
            }
        }

        if (spanSubtotal) spanSubtotal.textContent = `$${subtotal.toFixed(2)}`;
    });

    let descuentoCristian = tieneCristian ? 1000.0 : 0.0;
    let comisionDayana = ventasDayana * 0.03;
    let descuentoTotal = descuentoCristian + comisionDayana;

    const inputTransferencia = document.getElementById('dinero-transferencia');
    const totalTransferencias = inputTransferencia ? (parseFloat(inputTransferencia.value) || 0) : 0;

    // --- NUEVO: Extraer deudas del día ---
    const inputDeudas = document.getElementById('deudas-dia');
    const deudasDia = inputDeudas ? (parseFloat(inputDeudas.value) || 0) : 0;

    // --- MODIFICADO: Restar las deudas al total esperado ---
    let totalEsperado = totalBrutoGeneral - descuentoTotal - totalTransferencias - deudasDia;

    const elemTotalEsperado = document.getElementById('total-esperado');
    const elemComisionDayana = document.getElementById('txt-comision-dayana');
    const elemSalarioCristian = document.getElementById('txt-salario-cristian');

    if (elemTotalEsperado) {
        elemTotalEsperado.textContent = totalEsperado < 0
            ? `-$${Math.abs(totalEsperado).toFixed(2)}`
            : `$${totalEsperado.toFixed(2)}`;
    }

    if (elemComisionDayana) elemComisionDayana.textContent = `$${comisionDayana.toFixed(2)}`;
    if (elemSalarioCristian) elemSalarioCristian.textContent = `$${descuentoCristian.toFixed(2)}`;

    // --- NUEVO: Calcular y colorear Diferencia ---
    const inputEfectivo = document.getElementById('dinero-caja');
    const efectivoCaja = inputEfectivo ? (parseFloat(inputEfectivo.value) || 0) : 0;

    let diferencia = efectivoCaja - totalEsperado;

    const diffInput = document.getElementById('diferencia-caja');
    const diffIcon = document.getElementById('icono-diferencia');

    if (diffInput && diffIcon) {
        diffInput.value = diferencia.toFixed(2);
        
        let baseClasses = "w-28 bg-[#121316] border rounded-xl pl-7 pr-3 py-2.5 text-lg font-bold font-mono focus:outline-none cursor-not-allowed ";
        if (diferencia < 0) {
            diffInput.className = baseClasses + "border-rose-900/50 text-rose-400";
            diffIcon.className = "absolute left-3 top-1/2 -translate-y-1/2 font-bold text-rose-400";
        } else if (diferencia > 0) {
            diffInput.className = baseClasses + "border-emerald-900/50 text-emerald-400";
            diffIcon.className = "absolute left-3 top-1/2 -translate-y-1/2 font-bold text-emerald-400";
        } else {
            diffInput.className = baseClasses + "border-cyan-900/50 text-cyan-400";
            diffIcon.className = "absolute left-3 top-1/2 -translate-y-1/2 font-bold text-cyan-400";
        }
    }

    validarCierreCaja(totalEsperado);
}

async function enviarCierre() {
    const efectivoCaja = parseFloat(document.getElementById('dinero-caja').value) || 0;
    const totalTransferencias = parseFloat(document.getElementById('dinero-transferencia').value) || 0;
    const filas = document.querySelectorAll('.fila-producto');
    let productos = [];

    filas.forEach(fila => {
        const spanVendidosText = fila.querySelector('.vendidos').textContent;
        const vendidosVal = spanVendidosText === "Exceso físico" ? 0 : parseFloat(spanVendidosText) || 0;

        productos.push({
            id: fila.getAttribute('data-id'),
            entradas: parseFloat(fila.querySelector('.entradas').value) || 0,
            stock_final: parseFloat(fila.querySelector('.stock-final').value) || 0,
            vendidos: vendidosVal,
            subtotal: parseFloat(fila.querySelector('.subtotal').textContent.replace('$', '')) || 0
        });
    });

    try {
        const response = await fetch('/procesar_cierre', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                efectivo_caja: efectivoCaja,
                total_transferencias: totalTransferencias,
                productos: productos,
                deudas: [] // Array vacío ya que las deudas se gestionan en su vista independiente
            })
        });

        const res = await response.json();
        if (res.success) {
            alert(res.message);
            window.location.reload();
        } else {
            alert("Error: " + res.message);
        }
    } catch (err) {
        console.error("Error al procesar cierre:", err);
        alert("Ocurrió un error al procesar el cierre.");
    }
}

// ==========================================
// DETALLE DE CIERRE DE CAJA (HISTORIAL ADMIN)
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
        const gananciasPropietarios = res.ganancias_propietarios || {};
        const ventasBrutasPropietarios = res.ventas_brutas_propietarios || {};
        const descuentosPropietarios = res.descuentos_propietarios || {};

        document.getElementById('modal-cierre-titulo').textContent = `Detalle del Cierre #${cierre.id}`;
        document.getElementById('modal-cierre-subtitulo').textContent = `Fecha: ${cierre.fecha} | Responsable: ${cierre.usuario_nombre}`;
        document.getElementById('modal-total-esperado').textContent = `$${cierre.total_esperado.toFixed(2)}`;
        
        // Asignación de transferencias al modal
        const elTransf = document.getElementById('modal-total-transferencias');
        if (elTransf) {
            elTransf.textContent = `$${(cierre.total_transferencias || 0).toFixed(2)}`;
        }

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

        const contenedorPropietarios = document.getElementById('modal-ganancias-propietarios');
        if (contenedorPropietarios) {
            contenedorPropietarios.innerHTML = '';
            const propietariosSet = new Set([
                ...Object.keys(gananciasPropietarios),
                ...Object.keys(ventasBrutasPropietarios)
            ]);

            if (propietariosSet.size > 0) {
                propietariosSet.forEach(propietario => {
                    const ventaBruta = ventasBrutasPropietarios[propietario] || 0.0;
                    const gananciaFinal = gananciasPropietarios[propietario] || 0.0;
                    const infoDescuento = descuentosPropietarios[propietario];

                    let htmlDescuento = '';
                    if (infoDescuento && infoDescuento.label) {
                        htmlDescuento = `
                            <div class="flex justify-between items-center text-xs text-red-400/90 mt-0.5">
                                <span>(-) ${infoDescuento.label}:</span>
                                <span class="font-mono">-$${infoDescuento.monto.toFixed(2)}</span>
                            </div>
                        `;
                    }

                    contenedorPropietarios.innerHTML += `
                        <div class="bg-[#1a1b1e] p-3 rounded-xl border border-gray-800 text-left flex flex-col justify-between">
                            <div>
                                <span class="text-xs font-semibold text-gray-300 block truncate mb-1.5">${propietario}</span>
                                <div class="flex justify-between items-center text-xs text-gray-400 mb-0.5">
                                    <span>Venta Bruta:</span>
                                    <span class="font-mono text-white">$${ventaBruta.toFixed(2)}</span>
                                </div>
                                ${htmlDescuento}
                            </div>
                            <div class="border-t border-gray-800/80 pt-1.5 mt-2 flex justify-between items-center text-xs">
                                <span class="text-gray-400 font-medium">Ganancia Neta:</span>
                                <span class="font-mono font-bold text-orange-400">$${gananciaFinal.toFixed(2)}</span>
                            </div>
                        </div>
                    `;
                });
            } else {
                contenedorPropietarios.innerHTML = `<span class="text-xs text-gray-500 col-span-full">No hay registros de propietarios.</span>`;
            }
        }

        const tbody = document.getElementById('modal-tabla-detalles');
        if (tbody) {
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
        }

        const modal = document.getElementById('modal-detalle-cierre');
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
        }

    } catch (err) {
        console.error("Error consultando detalle del cierre:", err);
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
// VALIDACIÓN DE BOTÓN DE CIERRE
// ==========================================
function validarCierreCaja(totalEsperado) {
    const elDineroCaja = document.getElementById('dinero-caja');
    const btnCierre = document.getElementById('btn-cierre');

    if (!elDineroCaja || !btnCierre) return;

    const efectivoCaja = parseFloat(elDineroCaja.value) || 0;
    const hasDineroIngresado = efectivoCaja > 0;
    const hayVentas = totalEsperado >= 0;

    if (hasDineroIngresado && hayVentas) {
        btnCierre.disabled = false;
        btnCierre.classList.remove('bg-gray-800', 'text-gray-500', 'cursor-not-allowed');
        btnCierre.classList.add('bg-orange-600', 'hover:bg-orange-500', 'text-white', 'cursor-pointer');
    } else {
        btnCierre.disabled = true;
        btnCierre.classList.remove('bg-orange-600', 'hover:bg-orange-500', 'text-white', 'cursor-pointer');
        btnCierre.classList.add('bg-gray-800', 'text-gray-500', 'cursor-not-allowed');
    }
}

// ==========================================
// UTILIDADES
// ==========================================
function calcularSugerenciaVenta() {
    const inputCosto = document.getElementById('precio_costo');
    const inputVenta = document.getElementById('precio_venta');
    const textoSugerencia = document.getElementById('sugerencia_texto');

    if (!inputCosto || !inputVenta) return;

    const costo = parseFloat(inputCosto.value) || 0;

    if (costo > 0) {
        const sugerido = (costo * 1.30).toFixed(2);
        if (!inputVenta.value || parseFloat(inputVenta.value) === 0) {
            inputVenta.value = sugerido;
        }
        if (textoSugerencia) textoSugerencia.textContent = `Sugerido (+30%): $${sugerido}`;
    } else {
        if (textoSugerencia) textoSugerencia.textContent = '';
    }
}

// ==========================================
// EVENTOS AL CARGAR EL DOM
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const inputBuscador = document.getElementById('buscador');
    if (inputBuscador) {
        inputBuscador.addEventListener('keyup', filtrarProductos);
    }

    if (document.getElementById('tabla-productos')) {
        calcular();
    }
});