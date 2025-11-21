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
    const email = form.querySelector('#email').value;
    const password = form.querySelector('#password').value;

    // Función auxiliar para intentar login
    const tryLogin = async (url) => {
      const formData = new FormData();
      formData.append('email', email);
      formData.append('password', password);
      
      const resp = await fetch(url, { method: 'POST', body: formData });
      const isJson = resp.headers.get('content-type')?.includes('application/json');
      const data = isJson ? await resp.json() : {};
      return { 
        ok: resp.ok, 
        status: resp.status, 
        data, 
        detail: data.detail || resp.statusText 
      };
    };

    // Intenta primero login de empleado (admin)
    let result = await tryLogin('/empleado/login');
    let isAdmin = false;

    if (result.ok) {
      // Login exitoso como empleado/admin
      isAdmin = result.data?.es_admin !== false; // Por defecto true si no viene el campo
    } else if (result.status === 401) {
      // Si falla como admin, intenta como usuario normal
      result = await tryLogin('/login');
      isAdmin = false; // Los usuarios normales no son admin
    }

    if (result.ok) {
      const data = result.data || {};
      const nombre = data.name || data.nombre || data.email || 'usuario';
      showAlert(`✅ Bienvenido, <b>${nombre}</b>`, 'success');
      
      const destination = isAdmin ? '/admin' : '/home';
      setTimeout(() => window.location.href = destination, 800);
    } else {
      showAlert(result.detail || 'Credenciales inválidas', 'danger');
    }
  } catch (error) {
    console.error('Error en login:', error);
    showAlert('No se pudo contactar al servidor. Verifica la API.', 'danger');
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
});
