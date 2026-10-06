import { API_BASE_URL } from "./config.js";

window.addEventListener("pageshow", (event) => {
  if (
    event.persisted ||
    (window.performance && window.performance.navigation.type === 2)
  ) {
    const token = localStorage.getItem("access_token");
    if (!token) {
      window.location.replace("../login.html");
    }
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("loginForm");
  const signupForm = document.getElementById("signupForm");

  // Autocompletar el correo y el nombre en el formulario de registro si viene parametrizado (?email=...&name=...)
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

      const email = document.getElementById("loginEmail").value.trim();
      const password = document.getElementById("loginPassword").value;

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

      try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          const message =
            typeof errorData.detail === "object"
              ? JSON.stringify(errorData.detail)
              : errorData.detail || "Correo o contraseña incorrectos.";
          throw new Error(message);
        }

        const data = await response.json();
        localStorage.setItem("access_token", data.access_token);

        let userRole = data.user?.role || data.role;
        let userEmail = data.user?.email || data.email;

        if (!userRole || !userEmail) {
          const profileResponse = await fetch(`${API_BASE_URL}/users/me`, {
            headers: { Authorization: `Bearer ${data.access_token}` },
          });
          if (profileResponse.ok) {
            const profileData = await profileResponse.json();
            userRole = userRole || profileData.role;
            userEmail = userEmail || profileData.email;
          }
        }

        if (userRole) localStorage.setItem("user_role", userRole);
        if (userEmail) localStorage.setItem("user_email", normalizeUserEmail(userEmail));

        // REDIRECCIONES LIMPIAS
        if (userRole === "recruiter" || userRole === "admin") {
          window.location.href = "recruiter/jobs.html";
        } else {
          window.location.href = "candidate/dashboard.html";
        }
      } catch (error) {
        console.error("Error durante el inicio de sesión:", error);
        errorMessage.innerText = error.message;
        errorMessage.classList.remove("d-none");
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
        errorMessage.classList.add("d-none");
        errorMessage.innerText = "";
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
        console.error("Error durante el registro:", error);
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
    console.error("No se pudo obtener el perfil del usuario:", error);
    return null;
  }
}

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

  const navCandidateDashboard = document.getElementById(
    "navCandidateDashboard",
  );
  const navCandidateProfile = document.getElementById("navCandidateProfile");
  const navCandidateSettings = document.getElementById("navCandidateSettings");
  const navLoginBtn = document.getElementById("navLoginBtn");
  const navLogoutBtn = document.getElementById("navLogoutBtn");

  if (token) {
    if (navCandidateDashboard) navCandidateDashboard.classList.remove("d-none");
    if (navCandidateProfile) navCandidateProfile.classList.remove("d-none");
    if (navCandidateSettings) navCandidateSettings.classList.remove("d-none");
    if (navLogoutBtn) navLogoutBtn.classList.remove("d-none");
    if (navLoginBtn) navLoginBtn.classList.add("d-none");
  } else {
    if (navCandidateDashboard) navCandidateDashboard.classList.add("d-none");
    if (navCandidateProfile) navCandidateProfile.classList.add("d-none");
    if (navCandidateSettings) navCandidateSettings.classList.add("d-none");
    if (navLogoutBtn) navLogoutBtn.classList.add("d-none");
    if (navLoginBtn) navLoginBtn.classList.remove("d-none");
  }
}
