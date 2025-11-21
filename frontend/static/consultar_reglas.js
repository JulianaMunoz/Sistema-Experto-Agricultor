const estado = document.getElementById('estado');
const vacio = document.getElementById('vacio');
const contenedorTabla = document.getElementById('contenedorTabla');
const tbody = document.getElementById('tbodyReglas');
const filtro = document.getElementById('filtro');

let reglas = [];   // cache local para filtrar

function renderTabla(data) {
    tbody.innerHTML = '';
    data.forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td>${r.id}</td>
        <td>${r.factor} <span class="text-muted">(#${r.factor_id})</span></td>
        <td><code>${r.operador}</code></td>
        <td>${r.valor}</td>
        <td>${r.hecho} <span class="text-muted">(#${r.hecho_id})</span></td>
    `;
    tbody.appendChild(tr);
    });
}

function aplicarFiltro() {
    const q = filtro.value.trim().toLowerCase();
    if (!q) { renderTabla(reglas); return; }
    const filtradas = reglas.filter(r => {
    return (
        String(r.id).includes(q) ||
        String(r.factor_id).includes(q) ||
        String(r.hecho_id).includes(q) ||
        (r.factor || '').toLowerCase().includes(q) ||
        (r.hecho || '').toLowerCase().includes(q) ||
        (r.operador || '').toLowerCase().includes(q) ||
        String(r.valor).toLowerCase().includes(q)
    );
    });
    renderTabla(filtradas);
}

filtro.addEventListener('input', aplicarFiltro);

async function cargarReglas() {
    try {
    const resp = await fetch('/reglas');
    if (!resp.ok) throw new Error('Error al cargar reglas');
    const data = await resp.json();

    reglas = Array.isArray(data) ? data : [];
    if (reglas.length === 0) {
        vacio.classList.remove('d-none');
        contenedorTabla.classList.add('d-none');
    } else {
        renderTabla(reglas);
        contenedorTabla.classList.remove('d-none');
        vacio.classList.add('d-none');
    }
    } catch (e) {
    estado.className = 'alert alert-danger';
    estado.textContent = 'No se pudieron cargar las reglas. Verifica la API.';
    return;
    } finally {
    estado.classList.add('d-none');
    }
}

cargarReglas();