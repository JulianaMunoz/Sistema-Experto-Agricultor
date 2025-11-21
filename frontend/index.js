const form = document.getElementById('loginForm');
const btn = document.getElementById('btnSubmit');
const alertPlaceholder = document.getElementById('alertPlaceholder');

function showAlert(message, type = 'info') {
    alertPlaceholder.innerHTML = `
    <div class="alert alert-${type} alert-dismissible fade show" role="alert" style="max-width: 28rem; margin: 0 auto 1rem;">
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Cerrar"></button>
    </div>`;
}

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!form.checkValidity()) {
    showAlert('Por favor completa los campos requeridos.', 'warning');
    return;
    }

    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = 'Ingresando…';

    try {
    const formData = new FormData(form);
    const resp = await fetch(form.action, { method: 'POST', body: formData });

    const isJson = resp.headers.get('content-type')?.includes('application/json');
    if (resp.ok) {
const data = isJson ? await resp.json() : {};
showAlert(`✅ Bienvenido, <b>${data.name}</b>`, 'success');
setTimeout(() => window.location.href = "./templates/home", 1000);
} else {
        const err = isJson ? await resp.json() : { detail: 'Error desconocido' };
        showAlert(err.detail || 'Credenciales inválidas', 'danger');
    }
    } catch (error) {
    showAlert('No se pudo contactar al servidor. Verifica la API.', 'danger');
    } finally {
    btn.disabled = false;
    btn.textContent = originalText;
    }
});