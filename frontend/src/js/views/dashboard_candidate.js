//# Estado de postulación, edición de CV y barra de progreso con Modales Globales
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
// SISTEMA DE MODALES GLOBALES (Reemplaza alert y confirm)
// -------------------------------------------------------------
function showModalAlert(title, message) {
  return new Promise((resolve) => {
    document.getElementById("globalAlertTitle").textContent = title;
    document.getElementById("globalAlertMessage").textContent = message;

    const cancelBtn = document.getElementById("globalAlertCancelBtn");
    const confirmBtn = document.getElementById("globalAlertConfirmBtn");

    cancelBtn.style.display = "none";
    confirmBtn.textContent = "Aceptar";
    confirmBtn.className = "btn btn-primary px-4";

    const modalElement = document.getElementById("globalAlertModal");
    const modal = new bootstrap.Modal(modalElement);

    const handleHidden = () => {
      confirmBtn.removeEventListener("click", handleHidden);
      resolve();
    };
    modalElement.addEventListener("hidden.bs.modal", handleHidden, {
      once: true,
    });
    modal.show();
  });
}

function showModalConfirm(title, message, confirmButtonText = "Confirmar") {
  return new Promise((resolve) => {
    document.getElementById("globalAlertTitle").textContent = title;
    document.getElementById("globalAlertMessage").textContent = message;

    const cancelBtn = document.getElementById("globalAlertCancelBtn");
    const confirmBtn = document.getElementById("globalAlertConfirmBtn");

    cancelBtn.style.display = "block";
    cancelBtn.textContent = "Cancelar";
    confirmBtn.textContent = confirmButtonText;
    confirmBtn.className = "btn btn-success px-4";

    const modalElement = document.getElementById("globalAlertModal");
    const modal = new bootstrap.Modal(modalElement);

    let userConfirmed = false;

    const onConfirm = () => {
      userConfirmed = true;
      modal.hide();
    };

    const onCancel = () => {
      userConfirmed = false;
      modal.hide();
    };

    confirmBtn.onclick = onConfirm;
    cancelBtn.onclick = onCancel;

    const handleHidden = () => {
      confirmBtn.onclick = null;
      cancelBtn.onclick = null;
      resolve(userConfirmed);
    };

    modalElement.addEventListener("hidden.bs.modal", handleHidden, {
      once: true,
    });
    modal.show();
  });
}

// -------------------------------------------------------------
// Funciones del Dashboard (dashboard.html)
// -------------------------------------------------------------

async function loadDashboardData() {
  const token = localStorage.getItem("access_token");

  try {
    const response = await fetch(`${API_BASE_URL}/applications/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) throw new Error("Error al obtener las postulaciones");

    userApplications = await response.json();
    renderApplicationsTable(userApplications);

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

async function cancelApplication(applicationId) {
  const confirmed = await showModalConfirm(
    "Cancelar Postulación",
    "¿Estás seguro de que deseas cancelar esta postulación?\nEsta acción liberará tu espacio para postularte a otra vacante.",
    "Sí, cancelar",
  );
  if (!confirmed) return;

  try {
    const token = localStorage.getItem("access_token");
    const headers = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch(
      `${API_BASE_URL}/applications/${applicationId}`,
      {
        method: "DELETE",
        headers: headers,
      },
    );

    if (!response.ok) {
      const errData = await response.json();
      throw new Error(errData.detail || "No se pudo cancelar la postulación.");
    }

    await showModalAlert("Éxito", "Postulación cancelada con éxito.");

    if (typeof loadUserApplications === "function") {
      loadUserApplications();
    } else {
      location.reload();
    }
  } catch (error) {
    await showModalAlert("Error", `Error al cancelar: ${error.message}`);
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

  const totalMatch = apps.reduce((acc, app) => acc + (app.match_score || 0), 0);
  const avgMatch = Math.round(totalMatch / apps.length);
  if (statAvgMatch) statAvgMatch.textContent = `${avgMatch}%`;

  tableBody.innerHTML = apps
    .map((app) => {
      const detailsId = `candidate-match-${String(app.id).replace(/[^a-zA-Z0-9_-]/g, "")}`;
      return `
          <tr>
            <td class="fw-bold">${escapeHtml(app.job?.title || app.job_title || "Vacante sin título")}</td>
            <td>${formatApplicationDate(app.applied_at)}</td>
            <td>
              <span class="badge ${app.match_score >= 70 ? "bg-success" : "bg-warning text-dark"}">
                ${Math.round(app.match_score || 0)}% Match
              </span>
            </td>
            <td><span class="badge bg-primary">${escapeHtml(app.status || "Enviada")}</span></td>
            <td class="text-end">
              <div class="d-flex flex-wrap justify-content-end gap-1">
                <button class="btn btn-sm btn-outline-secondary view-job-btn" data-id="${escapeHtml(app.id)}">
                  <i class="bi bi-eye"></i> Ver vacante
                </button>
                <button
                  class="btn btn-sm btn-outline-primary"
                  type="button"
                  data-bs-toggle="collapse"
                  data-bs-target="#${detailsId}"
                  aria-expanded="false"
                  aria-controls="${detailsId}"
                >
                  <i class="bi bi-list-check"></i> Detalles del match
                </button>
                <button class="btn btn-sm btn-outline-danger cancel-app-btn" data-id="${escapeHtml(app.id)}">
                  <i class="bi bi-trash"></i> Cancelar
                </button>
              </div>
            </td>
          </tr>
          <tr>
            <td colspan="5" class="p-0 border-0">
              <div class="collapse" id="${detailsId}">
                <div class="card card-body border-0 bg-light m-2">
                  ${renderApplicationMatchDetails(app)}
                </div>
              </div>
            </td>
          </tr>
        `;
    })
    .join("");

  document.querySelectorAll(".view-job-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const appId = e.currentTarget.getAttribute("data-id");
      openJobModal(appId);
    });
  });

  document.querySelectorAll(".cancel-app-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const appId = e.currentTarget.getAttribute("data-id");
      cancelApplication(appId);
    });
  });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[character];
  });
}

function formatApplicationDate(value) {
  if (!value) return "No disponible";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "No disponible"
    : date.toLocaleDateString("es-ES");
}

function formatMatchScore(value) {
  const score = Number(value);
  if (!Number.isFinite(score)) return "No disponible";
  const percentage = score <= 1 ? score * 100 : score;
  return `${Math.round(percentage * 100) / 100}%`;
}

function renderMatchSkills(values, emptyMessage) {
  if (!Array.isArray(values) || values.length === 0) {
    return `<span class="text-muted">${escapeHtml(emptyMessage)}</span>`;
  }
  return values
    .map(
      (skill) =>
        `<span class="badge text-bg-light border me-1 mb-1">${escapeHtml(skill)}</span>`,
    )
    .join("");
}

function renderApplicationMatchDetails(app) {
  const exact = app.match_details?.exact_match || {};
  const semantic = app.match_details?.semantic_match || {};
  const analysis = app.ai_analysis || {};
  const renderTextList = (items, emptyMessage) => {
    if (!Array.isArray(items) || items.length === 0) {
      return `<li class="text-muted">${escapeHtml(emptyMessage)}</li>`;
    }
    return items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  };

  return `
    <div class="row g-3">
      <div class="col-md-6">
        <h6>Coincidencia exacta: ${formatMatchScore(exact.score)}</h6>
        <p class="small fw-semibold mb-1">Habilidades coincidentes</p>
        <div class="mb-2">${renderMatchSkills(exact.matched_skills, "Ninguna")}</div>
        <p class="small fw-semibold mb-1">Habilidades faltantes</p>
        <div class="mb-2">${renderMatchSkills(exact.missing_skills, "Ninguna")}</div>
        <p class="small fw-semibold mb-1">Otras habilidades</p>
        <div>${renderMatchSkills(exact.extra_skills, "Ninguna")}</div>
      </div>
      <div class="col-md-6">
        <h6>Coincidencia semántica: ${formatMatchScore(semantic.score)}</h6>
        <p class="small fw-semibold mb-1">Opinión</p>
        <p class="small">${escapeHtml(analysis.opinion || "Análisis no disponible.")}</p>
        <p class="small fw-semibold mb-1">Fortalezas</p>
        <ul class="small mb-2">${renderTextList(analysis.pros, "No disponibles.")}</ul>
        <p class="small fw-semibold mb-1">Riesgos / contras</p>
        <ul class="small mb-0">${renderTextList(analysis.cons, "No disponibles.")}</ul>
      </div>
    </div>
  `;
}

function openJobModal(applicationId) {
  const app = userApplications.find(
    (a) => String(a.id) === String(applicationId),
  );
  if (!app || !app.job) {
    showModalAlert(
      "Aviso",
      "No se encontró información detallada de esta vacante.",
    );
    return;
  }

  const job = app.job;

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

  const technicalSkillsContainer = document.getElementById(
    "modalTechnicalSkills",
  );
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
    "address",
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
    setInputValue("address", parsed.address || parsed.location);
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
        await showModalAlert(
          "Archivo Requerido",
          "Por favor selecciona un archivo PDF.",
        );
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
        const parsed = extracted.parsed_data || {};

        const aiNotice = document.getElementById("cvAiNotice");
        if (aiNotice) {
          const aiAvailable = extracted.ai_enrichment_status === "success";
          aiNotice.className = `alert alert-${aiAvailable ? "success" : "warning"} mt-3 mb-0`;
          aiNotice.textContent = aiAvailable
            ? "La IA enriqueció los datos extraídos. Revisa y corrige la información antes de guardarla."
            : "La IA no está disponible en este momento. Se muestran los datos de extracción automática; puedes revisarlos y completar el perfil manualmente.";
          aiNotice.setAttribute("role", aiAvailable ? "status" : "alert");
        }

        if (extracted.full_name || parsed.full_name)
          document.getElementById("fullName").value =
            extracted.full_name || parsed.full_name;
        if (extracted.email || parsed.email)
          document.getElementById("email").value =
            extracted.email || parsed.email;
        if (extracted.phone || parsed.phone)
          document.getElementById("phone").value =
            extracted.phone || parsed.phone;
        if (extracted.professional_title || parsed.professional_title)
          document.getElementById("currentTitle").value =
            extracted.professional_title || parsed.professional_title;
        const workExperience =
          extracted.work_experience || parsed.work_experience;
        if (workExperience) {
          document.getElementById("experienceSummary").value = Array.isArray(
            workExperience,
          )
            ? workExperience
                .map((item) =>
                  typeof item === "string" ? item : JSON.stringify(item),
                )
                .join("\n\n")
            : workExperience;
        }
        if (
          extracted.address ||
          extracted.location ||
          parsed.address ||
          parsed.location
        )
          document.getElementById("address").value =
            extracted.address ||
            extracted.location ||
            parsed.address ||
            parsed.location;
        const technicalSkills =
          extracted.technical_skills || parsed.technical_skills;
        if (Array.isArray(technicalSkills)) {
          document.getElementById("techSkills").value =
            technicalSkills.join(", ");
        }
        const softSkills = extracted.soft_skills || parsed.soft_skills;
        if (Array.isArray(softSkills)) {
          document.getElementById("softSkills").value = softSkills.join(", ");
        }
        if (parsed.more_info || extracted.more_info)
          document.getElementById("moreInfo").value =
            parsed.more_info || extracted.more_info;

        if (profileForm) {
          profileForm.dataset.rawText =
            extracted.raw_text || extracted.text || "";
        }

        updateProgressBar();
      } catch (err) {
        await showModalAlert("Error", "Ocurrió un error al analizar el PDF.");
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

      const existingResumeNotice =
        "Si ya tenías otro CV vinculado a tu cuenta, la información se actualizará y cualquier cambio en tu experiencia laboral o habilidades técnicas/blandas puede afectar tu visibilidad y match en procesos activos.";
      const hasExistingResume = Boolean(
        profileForm.dataset.rawText || document.getElementById("resumeIdBadge"),
      );

      if (hasExistingResume) {
        const confirmed = await showModalConfirm(
          "Actualizar CV",
          existingResumeNotice + "\n\n¿Deseas continuar?",
          "Sí, continuar",
        );
        if (!confirmed) return;
      }

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

      if (workExperience.length < 50) {
        await showModalAlert(
          "Validación",
          "El texto de la experiencia laboral es muy corto (mínimo 50 caracteres).",
        );
        return;
      }

      const rawText = profileForm.dataset.rawText || workExperience;
      const enteredEmail = document.getElementById("email")?.value || "";

      let safeEmail = enteredEmail;
      try {
        safeEmail =
          await window.PluriJobAuth.validateCandidateEmailForCurrentUser(
            enteredEmail,
          );
      } catch (error) {
        await showModalAlert("Error de validación", error.message);
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
          throw new Error(
            errData.detail || "Error guardando en la base de datos",
          );
        }

        await showModalAlert("¡Éxito!", "¡Perfil guardado correctamente!");
        updateProgressBar();
      } catch (error) {
        await showModalAlert("Error al guardar", error.message);
      }
    });
  }
}

function handleLogout(e) {
  if (e) e.preventDefault();
  localStorage.removeItem("access_token");
  localStorage.removeItem("user_role");
  window.location.href = "../login.html";
}
