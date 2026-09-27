import { API_BASE_URL } from "../config.js";

document.addEventListener("DOMContentLoaded", async () => {
  const token = localStorage.getItem("access_token");

  // 1. Verificación de autenticación
  if (!token) {
    console.warn("No hay token de sesión. Redirigiendo a login...");
    window.location.href = "/src/pages/login.html";
    return;
  }

  // 2. Evento de Logout (Configurado inmediatamente)
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", (e) => {
      e.preventDefault();
      localStorage.removeItem("access_token");
      window.location.href = "../../pages/login.html";
    });
  }

  // Instancias de Modales Bootstrap (si existen en el DOM)
  const candidatesModalElement = document.getElementById("candidatesModal");
  const cvDetailModalElement = document.getElementById("cvDetailModal");

  const candidatesModal = candidatesModalElement
    ? new bootstrap.Modal(candidatesModalElement)
    : null;
  const cvDetailModal = cvDetailModalElement
    ? new bootstrap.Modal(cvDetailModalElement)
    : null;

  // 3. Cargar vacantes al iniciar
  await loadJobs();

  // Función principal para obtener y renderizar vacantes
  async function loadJobs() {
    const activeContainer = document.getElementById("activeJobsList");

    try {
      // Ajuste de URL sin barra duplicada al final
      const response = await fetch(`${API_BASE_URL}/jobs`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          alert("Tu sesión ha expirado. Por favor inicia sesión de nuevo.");
          localStorage.removeItem("access_token");
          window.location.href = "/src/pages/login.html";
          return;
        }
        throw new Error(
          `Error ${response.status}: No se pudieron obtener las vacantes.`,
        );
      }

      const data = await response.json();

      // Adaptador: Soporta tanto si el backend responde con un Array directamente []
      // como si responde con formato de paginación { items: [] }
      const jobsList = Array.isArray(data) ? data : data.items || [];

      renderJobs(jobsList);
    } catch (error) {
      console.error("Error en loadJobs:", error);
      if (activeContainer) {
        activeContainer.innerHTML = `
          <div class="col-12">
            <div class="alert alert-danger" role="alert">
              <i class="bi bi-exclamation-triangle-fill me-2"></i>
              Error al cargar las vacantes. Revisa la consola del navegador (F12) o verifica el backend.
            </div>
          </div>
        `;
      }
    }
  }

  // Renderizar vacantes activas y cerradas
  function renderJobs(jobs) {
    const activeContainer = document.getElementById("activeJobsList");
    const closedContainer = document.getElementById("closedJobsList");

    if (!activeContainer || !closedContainer) return;

    const activeJobs = jobs.filter((j) => j.status === "active");
    const closedJobs = jobs.filter((j) => j.status === "closed");

    activeContainer.innerHTML = activeJobs.length
      ? activeJobs.map((job) => createJobCard(job, true)).join("")
      : '<div class="col-12"><p class="text-muted p-3">No tienes vacantes activas actualmente.</p></div>';

    closedContainer.innerHTML = closedJobs.length
      ? closedJobs.map((job) => createJobCard(job, false)).join("")
      : '<div class="col-12"><p class="text-muted p-3">No tienes vacantes cerradas.</p></div>';

    attachJobEventListeners();
  }

  // Plantilla HTML para una tarjeta de vacante
  function createJobCard(job, isActive) {
    const skills = job.required_skills || job.technical_skills || [];

    return `
      <div class="col-md-6 col-lg-4">
        <div class="card h-100 shadow-sm border-0">
          <div class="card-body d-flex flex-column">
            <div class="d-flex justify-content-between align-items-start mb-2">
              <h5 class="card-title text-primary mb-0">${job.title}</h5>
              <span class="badge ${isActive ? "bg-success" : "bg-secondary"}">
                ${(job.status || "active").toUpperCase()}
              </span>
            </div>
            <p class="card-text text-muted small mb-2">
              <i class="bi bi-building"></i> ${job.area || "N/A"} | 
              <i class="bi bi-laptop"></i> ${job.modality || job.work_mode || "N/A"}
            </p>
            <p class="card-text text-truncate flex-grow-1">${job.description || ""}</p>
            
            <div class="d-flex flex-wrap gap-1 mb-3">
              ${skills
                .slice(0, 3)
                .map(
                  (s) =>
                    `<span class="badge bg-light text-dark border">${s}</span>`,
                )
                .join("")}
            </div>

            <div class="d-flex justify-content-between align-items-center pt-2 border-top">
              <button class="btn btn-outline-primary btn-sm view-candidates-btn" data-job-id="${job.id}" data-job-title="${job.title}">
                <i class="bi bi-people"></i> Candidatos
              </button>
              
              ${
                isActive
                  ? `
                <button class="btn btn-outline-danger btn-sm toggle-status-btn" data-job-id="${job.id}" data-action="close">
                  <i class="bi bi-x-circle"></i> Cerrar
                </button>
              `
                  : `
                <button class="btn btn-outline-success btn-sm toggle-status-btn" data-job-id="${job.id}" data-action="reopen">
                  <i class="bi bi-arrow-counterclockwise"></i> Reabrir
                </button>
              `
              }
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // Asignar eventos a los botones de las tarjetas
  function attachJobEventListeners() {
    // Ver Candidatos
    document.querySelectorAll(".view-candidates-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const jobId = e.currentTarget.dataset.jobId;
        const jobTitle = e.currentTarget.dataset.jobTitle;
        const modalTitle = document.getElementById("candidatesModalTitle");
        if (modalTitle) modalTitle.innerText = `Candidatos: ${jobTitle}`;

        await loadCandidates(jobId);
        if (candidatesModal) candidatesModal.show();
      });
    });

    // Cerrar / Reabrir Vacante
    document.querySelectorAll(".toggle-status-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const jobId = e.currentTarget.dataset.jobId;
        const action = e.currentTarget.dataset.action;

        if (
          confirm(
            `¿Estás seguro de que deseas ${action === "close" ? "cerrar" : "reabrir"} esta vacante?`,
          )
        ) {
          await toggleJobStatus(jobId, action);
        }
      });
    });
  }

  // Cambiar estado de vacante (PATCH)
  async function toggleJobStatus(jobId, action) {
    try {
      const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/${action}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        await loadJobs();
      } else {
        alert("No se pudo cambiar el estado de la vacante.");
      }
    } catch (error) {
      console.error("Error al cambiar estado de vacante:", error);
    }
  }

  // Cargar candidatos de una vacante
  async function loadCandidates(jobId) {
    const container = document.getElementById("candidatesList");
    if (!container) return;

    container.innerHTML = `
      <div class="text-center py-4">
        <div class="spinner-border text-primary" role="status"></div>
        <p class="mt-2 text-muted">Calculando y ordenando coincidencias...</p>
      </div>
    `;

    try {
      const response = await fetch(
        `${API_BASE_URL}/jobs/${jobId}/applications`,
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );

      if (!response.ok) throw new Error("Error al obtener postulaciones");

      const data = await response.json();
      const applications = Array.isArray(data) ? data : data.items || [];

      if (!applications.length) {
        container.innerHTML =
          '<div class="alert alert-info">Aún no hay postulaciones para esta vacante.</div>';
        return;
      }

      // Ordenar por match_score desc
      applications.sort((a, b) => (b.match_score || 0) - (a.match_score || 0));

      container.innerHTML = applications
        .map((app) => createCandidateCard(app))
        .join("");
      attachCandidateEventListeners();
    } catch (error) {
      console.error("Error al cargar candidatos:", error);
      container.innerHTML =
        '<div class="alert alert-danger">Error al cargar candidatos.</div>';
    }
  }

  // Carta individual de candidato con Match %
  function createCandidateCard(app) {
    const score = Math.round(app.match_score || 0);
    let badgeBg = "bg-danger";
    if (score >= 85) badgeBg = "bg-success";
    else if (score >= 70) badgeBg = "bg-primary";
    else if (score >= 60) badgeBg = "bg-warning text-dark";

    const isRejected = app.status === "rejected";

    return `
      <div class="card border-0 shadow-sm ${isRejected ? "opacity-50 bg-light" : ""}">
        <div class="card-body d-flex justify-content-between align-items-center">
          <div>
            <h6 class="fw-bold mb-1">${app.resume?.full_name || "Candidato sin nombre"}</h6>
            <p class="text-muted small mb-1">
              <i class="bi bi-envelope"></i> ${app.resume?.email || "N/A"} | 
              <i class="bi bi-briefcase"></i> ${app.resume?.professional_title || "N/A"}
            </p>
            <span class="badge ${badgeBg}">Match: ${score}%</span>
            ${isRejected ? '<span class="badge bg-secondary ms-1">Descartado</span>' : ""}
          </div>

          <div class="d-flex gap-2">
            <button class="btn btn-outline-info btn-sm view-cv-btn" data-resume-id="${app.resume_id}">
              <i class="bi bi-file-earmark-person"></i> Ver CV
            </button>
            ${
              !isRejected
                ? `
              <button class="btn btn-outline-danger btn-sm reject-candidate-btn" data-app-id="${app.id}" data-job-id="${app.job_id}">
                <i class="bi bi-trash"></i> Descartar
              </button>
            `
                : ""
            }
          </div>
        </div>
      </div>
    `;
  }

  // Eventos para interactuar con Candidatos
  function attachCandidateEventListeners() {
    // Ver CV
    document.querySelectorAll(".view-cv-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const resumeId = e.currentTarget.dataset.resumeId;
        await loadCVDetail(resumeId);
        if (cvDetailModal) cvDetailModal.show();
      });
    });

    // Descartar Candidato
    document.querySelectorAll(".reject-candidate-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const appId = e.currentTarget.dataset.appId;
        const jobId = e.currentTarget.dataset.jobId;

        if (confirm("¿Deseas descartar a este candidato?")) {
          await rejectApplication(appId, jobId);
        }
      });
    });
  }

  // Cargar el detalle del CV
  async function loadCVDetail(resumeId) {
    const body = document.getElementById("cvDetailBody");
    if (!body) return;

    body.innerHTML =
      '<div class="spinner-border text-primary" role="status"></div>';

    try {
      const response = await fetch(`${API_BASE_URL}/resumes/${resumeId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const resume = await response.json();

      const nameElem = document.getElementById("cvCandidateName");
      if (nameElem)
        nameElem.innerText = resume.full_name || "Perfil de Candidato";

      body.innerHTML = `
        <h6><strong>Título Profesional:</strong> ${resume.professional_title || "N/A"}</h6>
        <p><strong>Ubicación:</strong> ${resume.location || "N/A"} | <strong>Teléfono:</strong> ${resume.phone || "N/A"}</p>
        <hr>
        <h6><strong>Habilidades Técnicas:</strong></h6>
        <p>${(resume.technical_skills || []).join(", ") || "Sin especificar"}</p>
        <h6><strong>Habilidades Blandas:</strong></h6>
        <p>${(resume.soft_skills || []).join(", ") || "Sin especificar"}</p>
        <hr>
        <h6><strong>Experiencia Laboral:</strong></h6>
        <p style="white-space: pre-line;">${resume.work_experience || "Sin experiencia registrada."}</p>
      `;
    } catch (error) {
      console.error("Error al cargar CV:", error);
      body.innerHTML =
        '<div class="alert alert-danger">Error al cargar el detalle del CV.</div>';
    }
  }

  // Descartar Aplicación (PATCH)
  async function rejectApplication(appId, jobId) {
    try {
      const response = await fetch(
        `${API_BASE_URL}/applications/${appId}/reject`,
        {
          method: "PATCH",
          headers: { Authorization: `Bearer ${token}` },
        },
      );

      if (response.ok) {
        await loadCandidates(jobId);
      } else {
        alert("No se pudo descartar al candidato.");
      }
    } catch (error) {
      console.error("Error al descartar candidato:", error);
    }
  }
});
