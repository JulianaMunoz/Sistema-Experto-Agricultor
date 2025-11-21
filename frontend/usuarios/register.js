const form = document.getElementById('registerForm');
const btn = document.getElementById('btnSubmit');
const alertPlaceholder = document.getElementById('alertPlaceholder');

function showAlert(message, type = 'info') {
    alertPlaceholder.innerHTML = `
    <div class="alert alert-${type} alert-dismissible fade show" role="alert" style="max-width: 36rem; margin: 0 auto 1rem;">
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Cerrar"></button>
    </div>`;
}

function validatePasswords() {
    const pass = document.getElementById('password');
    const confirm = document.getElementById('confirm');
    if (confirm.value !== pass.value) {
    confirm.setCustomValidity('Mismatch');
    } else {
    confirm.setCustomValidity('');
    }
}

document.getElementById('password').addEventListener('input', validatePasswords);
document.getElementById('confirm').addEventListener('input', validatePasswords);

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    validatePasswords();
    if (!form.checkValidity()) {
    form.classList.add('was-validated');
    showAlert('Revisa los campos resaltados.', 'warning');
    return;
    }

    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = 'Creando…';

    try {
    const formData = new FormData(form);
    const resp = await fetch(form.action, { method: 'POST', body: formData });

    const isJson = resp.headers.get('content-type')?.includes('application/json');
    if (resp.ok) {
        const data = isJson ? await resp.json() : {};
        showAlert(`✅ Cuenta creada para <b>${data.name}</b>. Ya puedes iniciar sesión.`, 'success');
        form.reset();
        form.classList.remove('was-validated');
        // Redirigir opcionalmente al login:
        // setTimeout(() => window.location.href = "/", 1200);
    } else {
        const err = isJson ? await resp.json() : { detail: 'Error desconocido' };
        showAlert(`❌ ${err.detail || 'No se pudo crear el usuario.'}`, 'danger');
    }
    } catch (error) {
    showAlert('No se pudo contactar al servidor. Verifica la API.', 'danger');
    } finally {
    btn.disabled = false;
    btn.textContent = originalText;
    }
});