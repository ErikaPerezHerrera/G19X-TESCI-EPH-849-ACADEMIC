import { API_BASE_URL } from "../config.js";

document.addEventListener("DOMContentLoaded", async () => {
  const token = localStorage.getItem("access_token");
  const userRole = localStorage.getItem("user_role");

  // Almacén local de vacantes cargadas para acceso rápido
  let currentJobs = [];

  // 1. Verificación de autenticación
  if (!token) {
    console.warn("No hay token de sesión. Redirigiendo a login...");
    window.location.href = "/src/pages/login.html";
    return;
  }

  const createRecruiterBtn = document.getElementById("createRecruiterBtn");
  if (userRole === "admin") {
    createRecruiterBtn?.classList.remove("d-none");
    createRecruiterBtn?.addEventListener("click", () => {
      const modalEl = document.getElementById("createRecruiterModal");
      if (modalEl) new bootstrap.Modal(modalEl).show();
    });

    const recruiterForm = document.getElementById("createRecruiterForm");
    recruiterForm?.addEventListener("submit", async (event) => {
      event.preventDefault();

      const name = document.getElementById("newRecruiterName").value.trim();
      const email = document.getElementById("newRecruiterEmail").value.trim();
      const password = document.getElementById("newRecruiterPassword").value;
      const errorBox = document.getElementById("recruiterCreateError");

      try {
        const response = await fetch(`${API_BASE_URL}/auth/register/recruiter`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            full_name: name,
            email,
            password,
            role: "recruiter",
          }),
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
          throw new Error(
            typeof data.detail === "string"
              ? data.detail
              : "No se pudo crear el reclutador.",
          );
        }

        alert("Reclutador creado correctamente.");
        recruiterForm.reset();
        bootstrap.Modal.getInstance(document.getElementById("createRecruiterModal"))?.hide();
      } catch (error) {
        if (errorBox) {
          errorBox.textContent = error.message;
          errorBox.classList.remove("d-none");
        } else {
          alert(error.message);
        }
      }
    });
  }

  // 2. Evento de Logout
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", (e) => {
      e.preventDefault();
      localStorage.removeItem("access_token");
      window.location.href = "../../pages/login.html";
    });
  }

  // Referencias a Secciones
  const jobsSection = document.getElementById("jobsSection");
  const candidatesSection = document.getElementById("candidatesSection");
  const backToJobsBtn = document.getElementById("backToJobsBtn");

  // Modales Bootstrap
  const cvDetailModalElement = document.getElementById("cvDetailModal");
  const cvDetailModal = cvDetailModalElement
    ? new bootstrap.Modal(cvDetailModalElement)
    : null;

  const jobDetailModalElement = document.getElementById("jobDetailModal");
  const jobDetailModal = jobDetailModalElement
    ? new bootstrap.Modal(jobDetailModalElement)
    : null;

  // Botón para regresar a las vacantes
  if (backToJobsBtn) {
    backToJobsBtn.addEventListener("click", () => {
      candidatesSection.classList.add("d-none");
      jobsSection.classList.remove("d-none");
    });
  }

  // 3. Cargar vacantes al iniciar
  await loadJobs();

  async function loadJobs() {
    const activeContainer = document.getElementById("activeJobsList");

    try {
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
      currentJobs = Array.isArray(data) ? data : data.items || [];

      renderJobs(currentJobs);
    } catch (error) {
      console.error("Error en loadJobs:", error);
      if (activeContainer) {
        activeContainer.innerHTML = `
          <div class="col-12">
            <div class="alert alert-danger" role="alert">
              <i class="bi bi-exclamation-triangle-fill me-2"></i>
              Error al cargar las vacantes. Revisa la consola del navegador.
            </div>
          </div>
        `;
      }
    }
  }

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

  function createJobCard(job, isActive) {
    const skills = job.technical_skills || job.soft_skills || [];

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
              <button class="btn btn-sm btn-outline-secondary view-job-btn" data-id="${job.id}">
                <i class="bi bi-eye"></i> Ver
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

  function attachJobEventListeners() {
    // Ver Candidatos
    document.querySelectorAll(".view-candidates-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const jobId = e.currentTarget.dataset.jobId;
        const jobTitle = e.currentTarget.dataset.jobTitle;

        const titleElem = document.getElementById("selectedJobTitle");
        if (titleElem) titleElem.innerText = `Candidatos: ${jobTitle}`;

        jobsSection.classList.add("d-none");
        candidatesSection.classList.remove("d-none");

        await loadCandidates(jobId);
      });
    });

    // Ver detalle de la vacante
    document.querySelectorAll(".view-job-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const jobId = e.currentTarget.getAttribute("data-id");
        openJobModal(jobId);
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

  // Función para poblar y abrir el Modal con el detalle de la vacante
  function openJobModal(jobId) {
    const job = currentJobs.find((j) => String(j.id) === String(jobId));

    if (!job) {
      alert("No se encontró información detallada de esta vacante.");
      return;
    }

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
      modalJobModality.textContent = job.modality || job.work_mode || "No especificado";

    const modalJobLocation = document.getElementById("modalJobLocation");
    if (modalJobLocation)
      modalJobLocation.textContent = job.location || "Remoto / No especificada";

    const modalJobDescription = document.getElementById("modalJobDescription");
    if (modalJobDescription)
      modalJobDescription.textContent =
        job.description || "Sin descripción disponible.";

    const modalJobDeadline = document.getElementById("modalJobDeadline");
    if (modalJobDeadline) {
      modalJobDeadline.textContent = job.deadline
        ? new Date(job.deadline).toLocaleDateString("es-ES")
        : "Sin fecha límite";
    }

    // --- Formatear Habilidades Técnicas ---
    const technicalSkillsContainer = document.getElementById("modalTechnicalSkills");
    if (technicalSkillsContainer) {
      technicalSkillsContainer.innerHTML = "";
      let technicalSkills = [];

      if (Array.isArray(job.technical_skills)) {
        technicalSkills = job.technical_skills;
      } else if (typeof job.technical_skills === "string") {
        technicalSkills = job.technical_skills
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
      }

      if (technicalSkills.length > 0) {
        technicalSkills.forEach((skill) => {
          technicalSkillsContainer.innerHTML += `<span class="badge bg-primary me-1 mb-1">${skill}</span>`;
        });
      } else {
        technicalSkillsContainer.innerHTML = `<span class="text-muted">Ninguna especificada</span>`;
      }
    }

    // --- Formatear Habilidades Blandas ---
    const softSkillsContainer = document.getElementById("modalSoftSkills");
    if (softSkillsContainer) {
      softSkillsContainer.innerHTML = "";
      let softSkills = [];

      if (Array.isArray(job.soft_skills)) {
        softSkills = job.soft_skills;
      } else if (typeof job.soft_skills === "string") {
        softSkills = job.soft_skills
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
      }

      if (softSkills.length > 0) {
        softSkills.forEach((skill) => {
          softSkillsContainer.innerHTML += `<span class="badge bg-secondary me-1 mb-1">${skill}</span>`;
        });
      } else {
        softSkillsContainer.innerHTML = `<span class="text-muted">Ninguna especificada</span>`;
      }
    }

    // Abrir el Modal de Bootstrap
    if (jobDetailModal) {
      jobDetailModal.show();
    } else {
      const modalElem = document.getElementById("jobDetailModal");
      if (modalElem) new bootstrap.Modal(modalElem).show();
    }
  }

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

  async function loadCandidates(jobId) {
    const container = document.getElementById("candidatesList");
    if (!container) return;

    container.innerHTML = `
      <div class="text-center py-4">
        <div class="spinner-border text-primary" role="status"></div>
        <p class="mt-2 text-muted">Cargando datos de los candidatos...</p>
      </div>
    `;

    try {
      const response = await fetch(
        `${API_BASE_URL}/jobs/${jobId}/applications`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (!response.ok) throw new Error("Error al obtener postulaciones");

      const data = await response.json();
      const applications = Array.isArray(data) ? data : data.items || [];

      if (!applications.length) {
        container.innerHTML =
          '<div class="alert alert-info">Aún no hay postulaciones para esta vacante.</div>';
        return;
      }

      const appsWithResume = await Promise.all(
        applications.map(async (app) => {
          if (!app.resume && app.resume_id) {
            try {
              const res = await fetch(`${API_BASE_URL}/resumes/${app.resume_id}`, {
                headers: { Authorization: `Bearer ${token}` },
              });
              if (res.ok) {
                app.resume = await res.json();
              }
            } catch (e) {
              console.error(`Error al cargar CV para ${app.resume_id}:`, e);
            }
          }
          return app;
        })
      );

      appsWithResume.sort((a, b) => (b.match_score || 0) - (a.match_score || 0));

      container.innerHTML = appsWithResume
        .map((app) => createCandidateCard(app))
        .join("");

      attachCandidateEventListeners();
    } catch (error) {
      console.error("Error al cargar candidatos:", error);
      container.innerHTML =
        '<div class="alert alert-danger">Error al cargar la lista de candidatos.</div>';
    }
  }

  function createCandidateCard(app) {
    const score = Math.round(app.match_score || 0);
    let badgeBg = "bg-danger";
    if (score >= 85) badgeBg = "bg-success";
    else if (score >= 70) badgeBg = "bg-primary";
    else if (score >= 60) badgeBg = "bg-warning text-dark";

    const isRejected = app.status === "rejected";

    const resume = app.resume || {};
    const parsed = resume.parsed_data || {};

    const candidateName =
      parsed.full_name ||
      parsed.name ||
      parsed.nombre ||
      resume.candidate_email ||
      app.candidate_email ||
      "Candidato sin nombre";

    const candidateEmail =
      app.candidate_email ||
      resume.candidate_email ||
      parsed.email ||
      "N/A";

    const professionalTitle =
      parsed.professional_title ||
      parsed.title ||
      parsed.titulo ||
      "Sin título especificado";

    return `
      <div class="card border-0 shadow-sm ${isRejected ? "opacity-50 bg-light" : ""}">
        <div class="card-body d-flex justify-content-between align-items-center">
          <div>
            <h6 class="fw-bold mb-1">${candidateName}</h6>
            <p class="text-muted small mb-1">
              <i class="bi bi-envelope"></i> ${candidateEmail} | 
              <i class="bi bi-briefcase"></i> ${professionalTitle}
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

  function attachCandidateEventListeners() {
    document.querySelectorAll(".view-cv-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const resumeId = e.currentTarget.dataset.resumeId;
        await loadCVDetail(resumeId);
        if (cvDetailModal) cvDetailModal.show();
      });
    });

    document.querySelectorAll(".reject-candidate-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();

        const appId = e.currentTarget.dataset.appId;
        const jobId = e.currentTarget.dataset.jobId;

        const reason = prompt("ADVERTENCIA: El descarte es PERMANENTE. Ingresa el motivo del descarte (opcional):");

        if (reason !== null) {
          await rejectApplication(appId, jobId, reason.trim());
        }
      });
    });
  }

  async function loadCVDetail(resumeId) {
    const body = document.getElementById("cvDetailBody");
    if (!body) return;

    body.innerHTML =
      '<div class="spinner-border text-primary" role="status"></div>';

    try {
      const response = await fetch(`${API_BASE_URL}/resumes/${resumeId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (!response.ok) throw new Error("Error al consultar el CV");

      const resume = await response.json();

      const parsed = resume.parsed_data || {};
      const techSkills = resume.extracted_skills || parsed.technical_skills || parsed.skills || [];
      const softSkills = parsed.soft_skills || [];

      const formattedTech = Array.isArray(techSkills) ? techSkills.join(", ") : techSkills;
      const formattedSoft = Array.isArray(softSkills) ? softSkills.join(", ") : softSkills;

      const nameElem = document.getElementById("cvCandidateName");
      if (nameElem) {
        nameElem.innerText = parsed.full_name || resume.candidate_email || "Perfil de Candidato";
      }

      body.innerHTML = `
        <h6><strong>Título Profesional:</strong> ${parsed.professional_title || "N/A"}</h6>
        <p><strong>Domicilio:</strong> ${parsed.address || "N/A"} | <strong>Teléfono:</strong> ${parsed.phone || "N/A"}</p>
        <hr>
        <h6><strong>Habilidades Técnicas:</strong></h6>
        <p>${formattedTech || "Sin especificar"}</p>
        <h6><strong>Habilidades Blandas:</strong></h6>
        <p>${formattedSoft || "Sin especificar"}</p>
        <hr>
        <h6><strong>Experiencia Laboral:</strong></h6>
        <p style="white-space: pre-line;">${parsed.work_experience || parsed.summary || "Sin experiencia registrada."}</p>
        <h6><strong>Más información</strong></h6>
        <p style="white-space: pre-line;">${parsed.more_info || "Sin información adicional."}</p>
      `;
    } catch (error) {
      console.error("Error al cargar CV:", error);
      body.innerHTML =
        '<div class="alert alert-danger">Error al cargar el detalle del CV.</div>';
    }
  }

  async function rejectApplication(appId, jobId, rejectionReason = "") {
    const token = localStorage.getItem("access_token");
    if (!token) {
      alert("Sesión no válida.");
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE_URL}/applications/${appId}/reject`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            rejection_reason: rejectionReason || null,
          }),
        }
      );

      if (response.ok) {
        await loadCandidates(jobId);
      } else {
        const errorData = await response.json();
        console.error("Detalle del error:", errorData);
        alert(`No se pudo descartar al candidato.`);
      }
    } catch (error) {
      console.error("Error al descartar candidato:", error);
    }
  }
});