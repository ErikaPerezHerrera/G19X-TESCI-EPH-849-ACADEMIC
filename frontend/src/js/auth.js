import { API_BASE_URL } from "./config.js";

// Protege las páginas con las que los usuarios pueden interactuar, pidiendo el token de inicio de sesión, o redirige a index
window.addEventListener("pageshow", (event) => {
  const isProtectedPage =
    window.location.pathname.includes("/recruiter/") ||
    window.location.pathname.includes("/candidate/");
  if (event.persisted && isProtectedPage) {
    const token = localStorage.getItem("access_token");
    if (!token) {
      window.location.replace("../login.html");
    }
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("loginForm");
  const signupForm = document.getElementById("signupForm");

  // Si es un registro de usuario, usa autocompletar el correo y el nombre en el formulario de registro si viene parametrizado (?email=...&name=...)
  if (signupForm) {
    const urlParams = new URLSearchParams(window.location.search);
    const emailParam = urlParams.get("email");
    const nameParam = urlParams.get("name");

    const signupEmailInput = document.getElementById("signupEmail");
    const signupNameInput = document.getElementById("signupName");

    if (emailParam && signupEmailInput) {
      signupEmailInput.value = decodeURIComponent(emailParam);
    }

    if (nameParam && signupNameInput) {
      signupNameInput.value = decodeURIComponent(nameParam);
    }
  }

  // Configurar botones de logout globales si existen en el DOM
  setupLogoutListeners();

  // Actualizar Navbar en index.html o cualquier página
  updateNavbarState();

  // --- LÓGICA DE LOGIN ---
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const email = document
        .getElementById("loginEmail")
        .value.trim()
        .toLowerCase();
      const password = document.getElementById("loginPassword").value;
      const submitButton = loginForm.querySelector('button[type="submit"]');

      let errorMessage = document.getElementById("errorMessage");
      if (!errorMessage) {
        errorMessage = document.createElement("div");
        errorMessage.id = "errorMessage";
        errorMessage.className = "alert alert-danger mt-3 d-none";
        loginForm.appendChild(errorMessage);
      } else {
        errorMessage.classList.add("d-none");
        errorMessage.innerText = "";
      }

      if (submitButton) {
        submitButton.disabled = true;
        submitButton.setAttribute("aria-busy", "true");
      }

      let sessionStarted = false;
      try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
          const message =
            typeof data.detail === "object"
              ? JSON.stringify(data.detail)
              : data.detail || "Correo o contraseña incorrectos.";
          throw new Error(message);
        }

        if (!data.access_token) {
          throw new Error("El servidor no devolvió un token de acceso válido.");
        }
        localStorage.setItem("access_token", data.access_token);
        sessionStarted = true;

        let userRole = data.user?.role || data.role || null;
        let userEmail = data.user?.email || data.email || null;

        if (!userRole || !userEmail) {
          const profileResponse = await fetch(`${API_BASE_URL}/users/me`, {
            headers: { Authorization: `Bearer ${data.access_token}` },
          });
          const profileData = await profileResponse.json().catch(() => ({}));
          if (!profileResponse.ok) {
            throw new Error(
              profileData.detail ||
                "Se inició sesión, pero no se pudo cargar el perfil. Inténtalo nuevamente.",
            );
          }
          userRole = userRole || profileData.role;
          userEmail = userEmail || profileData.email;
        }

        if (!userRole || !userEmail) {
          throw new Error(
            "El servidor autenticó la cuenta, pero no devolvió el rol o correo del usuario.",
          );
        }

        localStorage.setItem("user_role", userRole);
        localStorage.setItem("user_email", normalizeUserEmail(userEmail));

        // Redirecciones limpias al iniciar sesión
        if (userRole === "recruiter" || userRole === "admin") {
          window.location.href = "recruiter/jobs.html";
        } else {
          window.location.href = "candidate/dashboard.html";
        }
      } catch (error) {
        if (sessionStarted) {
          localStorage.removeItem("access_token");
          localStorage.removeItem("user_role");
          localStorage.removeItem("user_email");
        }
        errorMessage.textContent =
          error instanceof TypeError
            ? "No se pudo conectar con el servidor. Verifica que la API esté disponible e inténtalo nuevamente."
            : error.message || "No se pudo iniciar sesión.";
        errorMessage.classList.remove("d-none");
      } finally {
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.removeAttribute("aria-busy");
        }
      }
    });
  }

  // --- LÓGICA DE REGISTRO ---
  if (signupForm) {
    signupForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const fullName = document.getElementById("signupName").value.trim();
      const email = document.getElementById("signupEmail").value.trim();
      const password = document.getElementById("signupPassword").value;
      let errorMessage = document.getElementById("signupErrorMessage");

      if (!errorMessage) {
        errorMessage = document.createElement("div");
        errorMessage.id = "signupErrorMessage";
        errorMessage.className = "alert alert-danger mt-3 d-none";
        signupForm.appendChild(errorMessage);
      } else {
        // Ocultar y limpiar cualquier error previo
        errorMessage.classList.add("d-none");
        errorMessage.innerText = "";
      }

      // 2. Validar el nombre completo
      if (fullName.length < 10) {
        errorMessage.innerText =
          "Tu nombre completo debe tener al menos 10 caracteres.";
        errorMessage.classList.remove("d-none");
        return; // Detiene la ejecución para que no continúe hacia el try-catch
      }

      // 3. Validar la contraseña
      if (password.length < 12) {
        errorMessage.innerText = "Tu contraseña debe tener mínimo 12 caracteres.";
        errorMessage.classList.remove("d-none");
        return; // Detiene la ejecución para que no continúe hacia el try-catch
      }

      try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            full_name: fullName,
            email: email,
            password: password,
            role: "registered",
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          const message =
            typeof errorData.detail === "object"
              ? JSON.stringify(errorData.detail)
              : errorData.detail || "Error al registrar la cuenta.";
          throw new Error(message);
        }

        alert("¡Cuenta creada exitosamente! Ahora puedes iniciar sesión.");
        window.location.href = "login.html";
      } catch (error) {
        errorMessage.innerText = error.message;
        errorMessage.classList.remove("d-none");
      }
    });
  }
});

// --- MANEJO CENTRALIZADO DE LOGOUT ---
function setupLogoutListeners() {
  const logoutButtons = ["logoutBtn", "indexLogoutBtn"];

  logoutButtons.forEach((btnId) => {
    const btn = document.getElementById(btnId);
    if (btn) {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        localStorage.removeItem("access_token");
        localStorage.removeItem("user_role");
        localStorage.removeItem("user_email");

        // Si estás en una vista interna de candidato (pages/candidate/), subes dos niveles
        if (window.location.pathname.includes("/candidate/")) {
          window.location.href = "../login.html";
        } else {
          window.location.href = "login.html";
        }
      });
    }
  });
}

function normalizeUserEmail(value) {
  return String(value || "").trim().toLowerCase();
}

// Intenta consultar quien es el usuario actual y si está autenticado
async function fetchCurrentUserProfile(token = localStorage.getItem("access_token")) {
  if (!token) return null;

  try {
    const response = await fetch(`${API_BASE_URL}/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) return null;
    const profile = await response.json();
    return profile || null;
  } catch (error) {
    return null;
  }
}

// recupera, verifica y normaliza el correo electrónico del usuario autenticado utilizando el almacenamiento local del navegador
async function hydrateUserSessionInfo() {
  const token = localStorage.getItem("access_token");
  if (!token) return null;

  const storedEmail = localStorage.getItem("user_email");
  if (storedEmail) return normalizeUserEmail(storedEmail);

  const profile = await fetchCurrentUserProfile(token);
  if (profile?.email) {
    const normalizedEmail = normalizeUserEmail(profile.email);
    localStorage.setItem("user_email", normalizedEmail);
    return normalizedEmail;
  }

  return null;
}

// Revisa que el email del usuario actual sea el mismo que el del CV
async function validateCandidateEmailForCurrentUser(candidateEmail) {
  const expectedEmail = await hydrateUserSessionInfo();
  const actualEmail = normalizeUserEmail(candidateEmail);

  if (!expectedEmail) {
    if (actualEmail) {
      localStorage.setItem("user_email", actualEmail);
    }
    return actualEmail || "";
  }

  if (actualEmail && actualEmail !== expectedEmail) {
    throw new Error(
      `El correo del CV (${actualEmail}) no coincide con el correo de tu cuenta (${expectedEmail}).`,
    );
  }

  return expectedEmail;
}

window.PluriJobAuth = {
  normalizeUserEmail,
  fetchCurrentUserProfile,
  hydrateUserSessionInfo,
  validateCandidateEmailForCurrentUser,
};

// --- VISIBILIDAD DINÁMICA DEL NAVBAR (Para index.html) ---
function updateNavbarState() {
  const token = localStorage.getItem("access_token");

  const navCandidateDashboard = document.getElementById("navCandidateDashboard");
  const navCandidateProfile = document.getElementById("navCandidateProfile");
  const navLoginBtn = document.getElementById("navLoginBtn");
  const navLogoutBtn = document.getElementById("navLogoutBtn");
  const navSpanBadge = document.getElementById("navSpanBadge");

  if (token) {
    if (navCandidateDashboard) navCandidateDashboard.classList.remove("d-none");
    if (navCandidateProfile) navCandidateProfile.classList.remove("d-none");
    if (navLogoutBtn) navLogoutBtn.classList.remove("d-none");
    if (navLoginBtn) navLoginBtn.classList.add("d-none");
  } else {
    if (navCandidateDashboard) navCandidateDashboard.classList.add("d-none");
    if (navCandidateProfile) navCandidateProfile.classList.add("d-none");
    if (navLogoutBtn) navLogoutBtn.classList.add("d-none");
    if (navLoginBtn) navLoginBtn.classList.remove("d-none");
  }
}