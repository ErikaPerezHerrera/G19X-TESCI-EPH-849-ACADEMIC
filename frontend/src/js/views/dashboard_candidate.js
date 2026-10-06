//# Estado de postulación, edición de CV y barra de progreso
import { API_BASE_URL } from "../config.js";

// Variable global para almacenar las postulaciones cargadas y usarlas en el modal
let userApplications = [];

// Evitar que cargue la vista privada si se navega atrás sin token
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
  // 1. Verificación de autenticación
  const token = localStorage.getItem("access_token");
  if (!token) {
    console.warn("No hay token de sesión. Redirigiendo a login...");
    window.location.href = "../login.html";
    return;
  }

  // 2. Listener del botón Logout
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", handleLogout);
  }

  // 3. Inicializar funciones del Dashboard (dashboard.html)
  if (document.getElementById("applicationsTableBody")) {
    loadDashboardData();
  }

  // 4. Inicializar funciones del Perfil / CV (cv_profile.html)
  if (
    document.getElementById("profileForm") ||
    document.getElementById("extractCvForm")
  ) {
    loadProfileData();
    setupProfileFormListeners();
    setupProgressBarListeners();
  }
});

// -------------------------------------------------------------
// Funciones del Dashboard (dashboard.html)
// -------------------------------------------------------------

async function loadDashboardData() {
  const token = localStorage.getItem("access_token");

  try {
    // Obtener SOLO las postulaciones del usuario autenticado
    const response = await fetch(`${API_BASE_URL}/applications/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) throw new Error("Error al obtener las postulaciones");

    userApplications = await response.json();
    renderApplicationsTable(userApplications);

    // Cargar datos del CV del candidato para el saludo y badge
    const profileResponse = await fetch(`${API_BASE_URL}/resumes/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (profileResponse.ok) {
      const profileData = await profileResponse.json();
      const resume = Array.isArray(profileData) ? profileData[0] : profileData;

      const greeting = document.getElementById("candidateNameGreeting");
      if (greeting && resume?.parsed_data?.full_name) {
        greeting.textContent = resume.parsed_data.full_name;
      }

      const statCvStatus = document.getElementById("statCvStatus");
      if (statCvStatus) {
        if (resume && (resume.raw_text || resume.parsed_data)) {
          statCvStatus.textContent = "Cargado";
          statCvStatus.className = "badge bg-success";
        } else {
          statCvStatus.textContent = "Pendiente";
          statCvStatus.className = "badge bg-warning text-dark";
        }
      }
    }
  } catch (error) {
    console.error("Error al cargar dashboard:", error);
    const tableBody = document.getElementById("applicationsTableBody");
    if (tableBody) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center text-danger py-4">
            <i class="bi bi-exclamation-triangle me-2"></i> No se pudieron cargar las postulaciones.
          </td>
        </tr>
      `;
    }
  }
}

function renderApplicationsTable(apps) {
  const tableBody = document.getElementById("applicationsTableBody");
  const statApplications = document.getElementById("statApplications");
  const statAvgMatch = document.getElementById("statAvgMatch");

  if (!tableBody) return;

  if (statApplications) statApplications.textContent = apps.length;

  if (apps.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="5" class="text-center text-muted py-4">
          No tienes postulaciones registradas todavía. <a href="../index.html">Ver vacantes disponibles</a>.
        </td>
      </tr>
    `;
    return;
  }

  // Calcular Match Promedio
  const totalMatch = apps.reduce((acc, app) => acc + (app.match_score || 0), 0);
  const avgMatch = Math.round(totalMatch / apps.length);
  if (statAvgMatch) statAvgMatch.textContent = `${avgMatch}%`;

  // Renderizar filas soportando el modelo Application
  tableBody.innerHTML = apps
    .map(
      (app) => `
    <tr>
      <td class="fw-bold">${app.job?.title || app.job_title || "Vacante sin título"}</td>
      <td>${app.applied_at ? new Date(app.applied_at).toLocaleDateString("es-ES") : "Reciente"}</td>
      <td>
        <span class="badge ${app.match_score >= 70 ? "bg-success" : "bg-warning text-dark"}">
          ${Math.round(app.match_score || 0)}% Match
        </span>
      </td>
      <td><span class="badge bg-primary">${app.status || "Enviada"}</span></td>
      <td class="text-end">
        <button class="btn btn-sm btn-outline-secondary view-job-btn" data-id="${app.id}">
          <i class="bi bi-eye"></i> Ver
        </button>
      </td>
    </tr>
  `,
    )
    .join("");

  // Adjuntar event listeners a los botones "Ver"
  document.querySelectorAll(".view-job-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const appId = e.currentTarget.getAttribute("data-id");
      openJobModal(appId);
    });
  });
}

// Función para poblar y abrir el Modal con el detalle de la vacante
function openJobModal(applicationId) {
  const app = userApplications.find(
    (a) => String(a.id) === String(applicationId),
  );
  if (!app || !app.job) {
    alert("No se encontró información detallada de esta vacante.");
    return;
  }

  const job = app.job;

  // Cargar información general de la vacante
  const modalJobTitle = document.getElementById("modalJobTitle");
  if (modalJobTitle) modalJobTitle.textContent = job.title || "Sin título";

  const modalJobArea = document.getElementById("modalJobArea");
  if (modalJobArea) modalJobArea.textContent = job.area || "No especificado";

  const modalProfileType = document.getElementById("modalProfileType");
  if (modalProfileType)
    modalProfileType.textContent = job.profile_type || "No especificado";

  const modalJobModality = document.getElementById("modalJobModality");
  if (modalJobModality)
    modalJobModality.textContent = job.modality || "No especificado";

  const modalJobLocation = document.getElementById("modalJobLocation");
  if (modalJobLocation)
    modalJobLocation.textContent = job.location || "Remoto / No especificada";

  const modalJobDescription = document.getElementById("modalJobDescription");
  if (modalJobDescription)
    modalJobDescription.textContent =
      job.description || "Sin descripción disponible.";

  const modalAppliedAt = document.getElementById("modalAppliedAt");
  if (modalAppliedAt) {
    modalAppliedAt.textContent = app.applied_at
      ? new Date(app.applied_at).toLocaleString("es-ES")
      : "Reciente";
  }

  const modalJobDeadline = document.getElementById("modalJobDeadline");
  if (modalJobDeadline) {
    modalJobDeadline.textContent = job.deadline
      ? new Date(job.deadline).toLocaleDateString("es-ES")
      : "Sin fecha límite";
  }

  // Formatear Habilidades RTécnicas
  const technicalSkillsContainer = document.getElementById("modalTechnicalSkills");
  if (technicalSkillsContainer) {
    technicalSkillsContainer.innerHTML = "";
    const technicalSkills = Array.isArray(job.technical_skills)
      ? job.technical_skills
      : (job.technical_skills || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);

    if (technicalSkills.length > 0) {
      technicalSkills.forEach((skill) => {
        technicalSkillsContainer.innerHTML += `<span class="badge bg-primary me-1 mb-1">${skill}</span>`;
      });
    } else {
      technicalSkillsContainer.innerHTML = `<span class="text-muted">Ninguna especificada</span>`;
    }
  }

  // Formatear Habilidades Blandas
  const softSkillsContainer = document.getElementById("modalSoftSkills");
  if (softSkillsContainer) {
    softSkillsContainer.innerHTML = "";
    const softSkills = Array.isArray(job.soft_skills)
      ? job.soft_skills
      : (job.soft_skills || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);

    if (softSkills.length > 0) {
      softSkills.forEach((skill) => {
        softSkillsContainer.innerHTML += `<span class="badge bg-secondary me-1 mb-1">${skill}</span>`;
      });
    } else {
      softSkillsContainer.innerHTML = `<span class="text-muted">Ninguna especificada</span>`;
    }
  }

  // Instanciar y abrir el modal con el API JS de Bootstrap 5
  const modalElement = document.getElementById("jobDetailModal");
  if (modalElement) {
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  }
}

// -------------------------------------------------------------
// Funciones del Perfil / CV y Barra de Progreso (cv_profile.html)
// -------------------------------------------------------------

function updateProgressBar() {
  const fieldIds = [
    "fullName",
    "email",
    "phone",
    "currentTitle",
    "experienceSummary",
    "techSkills",
    "softSkills",
    "address"
  ];

  let completedFields = 0;
  const totalFields = fieldIds.length;

  fieldIds.forEach((id) => {
    const input = document.getElementById(id);
    if (input && input.value.trim() !== "") {
      completedFields++;
    }
  });

  const percentage = Math.round((completedFields / totalFields) * 100);

  const progressBar = document.getElementById("profileProgressBar");
  if (progressBar) {
    progressBar.style.width = `${percentage}%`;
    progressBar.setAttribute("aria-valuenow", percentage);
    progressBar.textContent = `${percentage}%`;

    progressBar.className =
      "progress-bar progress-bar-striped progress-bar-animated";
    if (percentage < 40) {
      progressBar.classList.add("bg-danger");
    } else if (percentage < 80) {
      progressBar.classList.add("bg-warning");
    } else {
      progressBar.classList.add("bg-success");
    }
  }
}

function setupProgressBarListeners() {
  const profileForm = document.getElementById("profileForm");
  if (profileForm) {
    profileForm.addEventListener("input", updateProgressBar);
    profileForm.addEventListener("change", updateProgressBar);
  }
}

async function loadProfileData() {
  const token = localStorage.getItem("access_token");
  if (!token) return;

  try {
    const response = await fetch(`${API_BASE_URL}/resumes/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) return;

    const responseData = await response.json();
    if (!responseData || responseData.length === 0) return;

    const data = Array.isArray(responseData) ? responseData[0] : responseData;
    if (!data) return;

    const parsed = data.parsed_data || {};

    const profileForm = document.getElementById("profileForm");
    if (profileForm) {
      profileForm.dataset.rawText = data.raw_text || "";
    }

    const setInputValue = (id, val) => {
      const input = document.getElementById(id);
      if (input) input.value = val || "";
    };

    setInputValue("fullName", parsed.full_name);
    setInputValue("email", data.candidate_email || parsed.email);
    setInputValue("phone", parsed.phone);
    setInputValue("address", parsed.address||parsed.location);
    setInputValue("currentTitle", parsed.professional_title);
    setInputValue("experienceSummary", parsed.work_experience);
    setInputValue("moreInfo", parsed.more_info);

    const techSkills = parsed.technical_skills || data.extracted_skills || [];
    const softSkills = parsed.soft_skills || [];

    setInputValue(
      "techSkills",
      Array.isArray(techSkills) ? techSkills.join(", ") : techSkills,
    );
    setInputValue(
      "softSkills",
      Array.isArray(softSkills) ? softSkills.join(", ") : softSkills,
    );

    const resumeBadge = document.getElementById("resumeIdBadge");
    if (resumeBadge && data.id) {
      resumeBadge.textContent = `ID: ${data.id.substring(0, 8)}...`;
      resumeBadge.classList.remove("d-none");
    }

    updateProgressBar();
  } catch (error) {
    console.error("Error al cargar la información del CV:", error);
  }
}

function setupProfileFormListeners() {
  const extractCvForm = document.getElementById("extractCvForm");
  const profileForm = document.getElementById("profileForm");

  if (extractCvForm) {
    extractCvForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fileInput = document.getElementById("cvPdfInput");
      const file = fileInput?.files[0];

      if (!file) {
        alert("Por favor selecciona un archivo PDF.");
        return;
      }

      const formData = new FormData();
      formData.append("file", file);

      const token = localStorage.getItem("access_token");
      const progress = document.getElementById("extractionProgress");
      const btn = document.getElementById("btnExtractCv");

      if (progress) progress.classList.remove("d-none");
      if (btn) btn.disabled = true;

      try {
        const response = await fetch(`${API_BASE_URL}/resumes/extract`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        });

        if (!response.ok) {
          const errData = await response.json();
          throw new Error(errData.detail || "Error procesando el PDF");
        }

        const extracted = await response.json();

        if (extracted.full_name)
          document.getElementById("fullName").value = extracted.full_name;
        if (extracted.email)
          document.getElementById("email").value = extracted.email;
        if (extracted.phone)
          document.getElementById("phone").value = extracted.phone;
        if (extracted.professional_title)
          document.getElementById("currentTitle").value =
            extracted.professional_title;
        if (extracted.work_experience)
          document.getElementById("experienceSummary").value =
            extracted.work_experience;
        if (extracted.address || extracted.location)
          document.getElementById("address").value =
            extracted.address || extracted.location;
        if (Array.isArray(extracted.technical_skills)) {
          document.getElementById("techSkills").value =
            extracted.technical_skills.join(", ");
        }
        if (Array.isArray(extracted.soft_skills)) {
          document.getElementById("softSkills").value =
            extracted.soft_skills.join(", ");
        }
        if (extracted.parsed_data.more_info)
          document.getElementById("moreInfo").value =
            extracted.parsed_data.more_info;        

        if (profileForm) {
          profileForm.dataset.rawText =
            extracted.raw_text || extracted.text || "";
        }

        updateProgressBar();
      } catch (err) {
        console.error("Error al extraer PDF:", err);
        alert(`Ocurrió un error al analizar el PDF: ${err.message}`);
      } finally {
        if (progress) progress.classList.add("d-none");
        if (btn) btn.disabled = false;
      }
    });
  }

  if (profileForm) {
    profileForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const token = localStorage.getItem("access_token");
      if (!token) return;

      const techSkillsStr = document.getElementById("techSkills")?.value || "";
      const softSkillsStr = document.getElementById("softSkills")?.value || "";

      const techSkillsArray = techSkillsStr
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const softSkillsArray = softSkillsStr
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const allSkills = [...techSkillsArray, ...softSkillsArray];

      const workExperience =
        document.getElementById("experienceSummary")?.value || "";

      const rawText = profileForm.dataset.rawText || workExperience;
      const enteredEmail = document.getElementById("email")?.value || "";

      let safeEmail = enteredEmail;
      try {
        safeEmail = await window.PluriJobAuth.validateCandidateEmailForCurrentUser(
          enteredEmail,
        );
      } catch (error) {
        alert(error.message);
        return;
      }

      const payload = {
        candidate_email: safeEmail,
        raw_text: rawText,
        extracted_skills: allSkills,
        parsed_data: {
          full_name: document.getElementById("fullName")?.value || "",
          phone: document.getElementById("phone")?.value || "",
          address: document.getElementById("address")?.value || "",
          professional_title:
            document.getElementById("currentTitle")?.value || "",
          technical_skills: techSkillsArray,
          soft_skills: softSkillsArray,
          work_experience: workExperience,
          more_info: document.getElementById("moreInfo")?.value || "",
        },
      };

      try {
        const response = await fetch(`${API_BASE_URL}/resumes`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const errData = await response.json();
          throw new Error(errData.detail || "Error guardando en la BD");
        }

        alert("¡Perfil guardado correctamente!");
        updateProgressBar();
      } catch (error) {
        console.error("Error al guardar:", error);
        alert(`Error al guardar: ${error.message}`);
      }
    });
  }
}

// -------------------------------------------------------------
// Cierre de Sesión
// -------------------------------------------------------------
function handleLogout(e) {
  if (e) e.preventDefault();
  localStorage.removeItem("access_token");
  localStorage.removeItem("user_role");
  window.location.href = "../login.html";
}