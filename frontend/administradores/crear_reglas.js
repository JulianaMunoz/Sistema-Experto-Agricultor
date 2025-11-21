// elementos
const selectFactor = document.getElementById('selectFactor');
const selectHecho = document.getElementById('selectHecho');
const btnNewFactor = document.getElementById('btnNewFactor');
const btnNewHecho = document.getElementById('btnNewHecho');
const btnCrearRegla = document.getElementById('btnCrearRegla');
const inputValor = document.getElementById('inputValor');
const selectOperador = document.getElementById('selectOperador');
const msgCreate = document.getElementById('msgCreate');

// modales/forms
const modalFactorEl = document.getElementById('modalFactor');
const modalHechoEl = document.getElementById('modalHecho');
const bsModalFactor = new bootstrap.Modal(modalFactorEl);
const bsModalHecho = new bootstrap.Modal(modalHechoEl);
const formFactor = document.getElementById('formFactor');
const formHecho = document.getElementById('formHecho');

// Cargar initial datos
async function loadOptions() {
try {
    const [fResp, hResp] = await Promise.all([fetch('/factores/'), fetch('/hechos/')]);
    if (!fResp.ok || !hResp.ok) throw new Error('Error al obtener datos');

    const factores = await fResp.json();
    const hechos = await hResp.json();

    // limpiar y poblar
    selectFactor.innerHTML = '<option value="">-- Seleccione factor --</option>';
    factores.forEach(f => {
    const opt = document.createElement('option');
    opt.value = f.id;
    // usa nombre si existe o id como fallback
    opt.textContent = (f.nombre || `Factor #${f.id}`).toString();
    selectFactor.appendChild(opt);
    });

    selectHecho.innerHTML = '<option value="">-- Seleccione hecho --</option>';
    hechos.forEach(h => {
    const opt = document.createElement('option');
    opt.value = h.id;
    opt.textContent = ( (h.descripcion && h.descripcion.length > 40) ? h.descripcion.slice(0,40)+'…' : h.descripcion ) || `Hecho #${h.id}`;
    selectHecho.appendChild(opt);
    });
} catch (e) {
    console.error(e);
    msgCreate.innerHTML = `<div class="alert alert-danger">No fue posible cargar factores/hechos. Verifica la API.</div>`;
}
}

// crear regla
btnCrearRegla.addEventListener('click', async () => {
msgCreate.innerHTML = '';
const factor_id = selectFactor.value;
const hecho_id = selectHecho.value;
const operador = selectOperador.value;
const valor = inputValor.value && inputValor.value.trim();

// validacion sencilla
if (!factor_id || !hecho_id || !valor) {
    msgCreate.innerHTML = `<div class="alert alert-warning">Completa Factor, Hecho y Valor.</div>`;
    return;
}

// para rango, valida formato x-y
if (operador === 'range' && !/^\s*\d+\s*-\s*\d+\s*$/.test(valor)) {
    msgCreate.innerHTML = `<div class="alert alert-warning">Formato de rango inválido. Ej: 1000-2000</div>`;
    return;
}

try {
    const resp = await fetch('/reglas/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ factor_id: Number(factor_id), hecho_id: Number(hecho_id), operador: operador === 'range' ? '=' : operador, valor })
    });

    if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(errText || 'Error creando regla');
    }

    const created = await resp.json();
    msgCreate.innerHTML = `<div class="alert alert-success">Regla creada (ID: ${created.id}).</div>`;
    // limpiar inputs
    inputValor.value = '';
    selectOperador.value = '=';
    // si tienes una tabla de reglas, podrías recargarla aquí (emitir evento / llamar función)
} catch (e) {
    console.error(e);
    msgCreate.innerHTML = `<div class="alert alert-danger">No se pudo crear la regla. ${e.message}</div>`;
}
});

// abrir modal crear factor
btnNewFactor.addEventListener('click', () => {
document.getElementById('factorNombre').value = '';
document.getElementById('factorCategoria').value = '';
document.getElementById('msgFactor').innerHTML = '';
bsModalFactor.show();
});

// crear factor via API y actualizar select
formFactor.addEventListener('submit', async (ev) => {
ev.preventDefault();
const nombre = document.getElementById('factorNombre').value.trim();
const categoria = document.getElementById('factorCategoria').value.trim();
if (!nombre || !categoria) {
    document.getElementById('msgFactor').innerHTML = `<div class="alert alert-warning">Nombre y categoría son requeridos.</div>`;
    return;
}
try {
    const resp = await fetch('/factores/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ nombre, categoria })
    });
    if (!resp.ok) throw new Error('Error creando factor');
    const created = await resp.json();
    bsModalFactor.hide();
    await loadOptions();
    selectFactor.value = created.id;
    document.getElementById('msgCreate').innerHTML = `<div class="alert alert-success">Factor creado.</div>`;
} catch (e) {
    console.error(e);
    document.getElementById('msgFactor').innerHTML = `<div class="alert alert-danger">No se pudo crear factor.</div>`;
}
});

// abrir modal crear hecho
btnNewHecho.addEventListener('click', () => {
document.getElementById('hechoDescripcion').value = '';
document.getElementById('msgHecho').innerHTML = '';
bsModalHecho.show();
});

// crear hecho via API y actualizar select
formHecho.addEventListener('submit', async (ev) => {
ev.preventDefault();
const descripcion = document.getElementById('hechoDescripcion').value.trim();
if (!descripcion) {
    document.getElementById('msgHecho').innerHTML = `<div class="alert alert-warning">Descripción requerida.</div>`;
    return;
}
try {
    const resp = await fetch('/hechos/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ descripcion })
    });
    if (!resp.ok) throw new Error('Error creando hecho');
    const created = await resp.json();
    bsModalHecho.hide();
    await loadOptions();
    selectHecho.value = created.id;
    document.getElementById('msgCreate').innerHTML = `<div class="alert alert-success">Hecho creado.</div>`;
} catch (e) {
    console.error(e);
    document.getElementById('msgHecho').innerHTML = `<div class="alert alert-danger">No se pudo crear hecho.</div>`;
}
});

// initial
loadOptions();