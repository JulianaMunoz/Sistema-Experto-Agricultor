const estado = document.getElementById('estado');
const vacio = document.getElementById('vacio');
const contenedorTabla = document.getElementById('contenedorTabla');
const tbody = document.getElementById('tbodyReglas');
const filtro = document.getElementById('filtro');

let reglas = [];   // cache local para filtrar
let mapFactores = {};
let mapHechos = {};

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
        <td class="text-nowrap">
          <button class="btn btn-sm btn-outline-primary" onclick="editarRegla(${r.id})">Editar</button>
          <button class="btn btn-sm btn-danger" onclick="eliminarRegla(${r.id})">Eliminar</button>
        </td>
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
        const [respReglas, respFactores, respHechos] = await Promise.all([
            fetch('/reglas'),
            fetch('/factores'),
            fetch('/hechos')
        ]);
        if (!respReglas.ok) throw new Error('Error al cargar reglas');

        const dataReglas = await respReglas.json();
        const dataFactores = respFactores.ok ? await respFactores.json() : [];
        const dataHechos = respHechos.ok ? await respHechos.json() : [];

        mapFactores = {};
        dataFactores.forEach(f => { mapFactores[f.id] = f.nombre; });
        mapHechos = {};
        dataHechos.forEach(h => { mapHechos[h.id] = h.descripcion; });

        reglas = (Array.isArray(dataReglas) ? dataReglas : []).map(r => ({
            ...r,
            factor: mapFactores[r.factor_id] || 'N/A',
            hecho: mapHechos[r.hecho_id] || 'N/A'
        }));

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

async function eliminarRegla(id) {
    const regla = reglas.find(r => r.id === id);
    if (!regla) return;

    const result = await Swal.fire({
        title: `Eliminar regla #${id}`,
        html: `<p>¿Seguro que quieres eliminar la regla relacionada con <strong>${regla.factor_nombre ?? 'este factor'}</strong>?</p>`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Eliminar',
        cancelButtonText: 'Cancelar',
        focusConfirm: false,
        reverseButtons: true,
        preConfirm: async () => {
            // Este retorno permite que Swal muestre el loader mientras ocurre el fetch
            try {
                const resp = await fetch(`/reglas/${id}`, { method: 'DELETE' });
                if (!resp.ok) {
                    const text = await resp.text().catch(() => 'Error desconocido');
                    throw new Error(text || 'No se pudo eliminar la regla');
                }
                return true;
            } catch (err) {
                // Si ocurre un error, Swal mostrará el mensaje de validación y no cerrará el modal
                Swal.showValidationMessage(`Error: ${err.message}`);
                return false;
            }
        },
        allowOutsideClick: () => !Swal.isLoading()
    });

    if (result.isConfirmed && result.value) {
        // Actualiza estado local y UI
        reglas = reglas.filter(r => r.id !== id);
        // Si usas cargarReglas() en otros lados, podrías llamarla en lugar de aplicarFiltro()
        aplicarFiltro();
        Swal.fire('Eliminado', 'La regla fue eliminada correctamente.', 'success');
    }
}


cargarReglas();

function buildOptions(map) {
    const entries = Object.entries(map).sort((a, b) => a[1].localeCompare(b[1]));
    return entries.map(([id, nombre]) => `<option value="${id}">${nombre} (#${id})</option>`).join('');
}

async function crearRegla() {
    await Swal.fire({
        title: 'Nueva regla',
        html: `
          <select id="swal-factor" class="form-select mb-2">${buildOptions(mapFactores)}</select>
          <select id="swal-hecho" class="form-select mb-2">${buildOptions(mapHechos)}</select>
          <input id="swal-operador" class="form-control mb-2" placeholder="Operador (=, <=, >=)" value="=">
          <input id="swal-valor" class="form-control" placeholder="Valor">
        `,
        focusConfirm: false,
        showCancelButton: true,
        confirmButtonText: 'Guardar',
        preConfirm: () => {
            const factor_id = Number(document.getElementById('swal-factor').value);
            const hecho_id = Number(document.getElementById('swal-hecho').value);
            const operador = document.getElementById('swal-operador').value.trim();
            const valor = document.getElementById('swal-valor').value.trim();
            if (!factor_id || !hecho_id || !operador || !valor) {
                Swal.showValidationMessage('Completa todos los campos');
                return;
            }
            return { factor_id, hecho_id, operador, valor };
        }
    }).then(async (res) => {
        if (!res.isConfirmed) return;
        try {
            const resp = await fetch('/reglas/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(res.value)
            });
            if (!resp.ok) throw new Error('Error al crear regla');
            await cargarReglas();
            Swal.fire('Listo', 'Regla creada', 'success');
        } catch (e) {
            Swal.fire('Error', 'No se pudo crear la regla', 'error');
        }
    });
}

async function editarRegla(id) {
    const regla = reglas.find(r => r.id === id);
    if (!regla) return;
    await Swal.fire({
        title: `Editar regla #${id}`,
        html: `
          <select id="swal-factor" class="form-select mb-2">${buildOptions(mapFactores)}</select>
          <select id="swal-hecho" class="form-select mb-2">${buildOptions(mapHechos)}</select>
          <input id="swal-operador" class="form-control mb-2" placeholder="Operador (=, <=, >=)" value="${regla.operador}">
          <input id="swal-valor" class="form-control" placeholder="Valor" value="${regla.valor}">
        `,
        didOpen: () => {
            document.getElementById('swal-factor').value = regla.factor_id;
            document.getElementById('swal-hecho').value = regla.hecho_id;
        },
        focusConfirm: false,
        showCancelButton: true,
        confirmButtonText: 'Guardar',
        preConfirm: () => {
            const factor_id = Number(document.getElementById('swal-factor').value);
            const hecho_id = Number(document.getElementById('swal-hecho').value);
            const operador = document.getElementById('swal-operador').value.trim();
            const valor = document.getElementById('swal-valor').value.trim();
            if (!factor_id || !hecho_id || !operador || !valor) {
                Swal.showValidationMessage('Completa todos los campos');
                return;
            }
            return { factor_id, hecho_id, operador, valor };
        }
    }).then(async (res) => {
        if (!res.isConfirmed) return;
        try {
            const resp = await fetch(`/reglas/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(res.value)
            });
            if (!resp.ok) throw new Error('Error al actualizar');
            await cargarReglas();
            Swal.fire('Listo', 'Regla actualizada', 'success');
        } catch (e) {
            Swal.fire('Error', 'No se pudo actualizar la regla', 'error');
        }
    });
}
cargarReglas();
