import { API_BASE_URL } from "../config.js";

document.addEventListener("DOMContentLoaded", async () => {
  const token = localStorage.getItem("access_token");
  const userRole = localStorage.getItem("user_role");

  // Almacén local de vacantes cargadas para acceso rápido
  let currentJobs = [];
  let currentCandidateApplications = [];

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

    // Escuchador para el botón de Crear Reclutador, disponible solo para usuario con rol Admin
    const recruiterForm = document.getElementById("createRecruiterForm");
    recruiterForm?.addEventListener("submit", async (event) => {
      event.preventDefault();

      const name = document.getElementById("newRecruiterName").value.trim();
      const email = document.getElementById("newRecruiterEmail").value.trim();
      const password = document.getElementById("newRecruiterPassword").value;
      const errorBox = document.getElementById("recruiterCreateError");

      try {
        const response = await fetch(
          `${API_BASE_URL}/auth/register/recruiter`,
          {
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
          },
        );

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
        bootstrap.Modal.getInstance(
          document.getElementById("createRecruiterModal"),
        )?.hide();
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
  const candidatesSortSelect = document.getElementById("candidateMatchSort");
  candidatesSortSelect?.addEventListener("change", renderCandidateCards);
  const jobSearchInput = document.getElementById("jobSearchInput");
  const filterJobs = () => {
    const query = (jobSearchInput?.value || "").trim().toLocaleLowerCase();
    if (!query) {
      renderJobs(currentJobs);
      return;
    }
    // Al usar el buscador en el dashboard del reclutador, puede encontrar vacantes según coincidencias del texto en el título, descripción, area, perfil, modalidad, ubicación, habilidades
    const filteredJobs = currentJobs.filter((job) => {
      const searchableText = [
        job.title,
        job.description,
        job.area,
        job.profile_type,
        job.modality,
        job.location,
        ...(Array.isArray(job.technical_skills) ? job.technical_skills : []),
        ...(Array.isArray(job.soft_skills) ? job.soft_skills : []),
      ]
        .filter((value) => typeof value === "string")
        .join(" ")
        .toLocaleLowerCase();
      return searchableText.includes(query);
    });
    renderJobs(filteredJobs);
  };
  document
    .getElementById("jobSearchButton")
    ?.addEventListener("click", filterJobs);
  jobSearchInput?.addEventListener("input", filterJobs);
  jobSearchInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") filterJobs();
  });

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

  // Cargar vacantes al iniciar
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
      if (activeContainer) {
        activeContainer.innerHTML = `
          <div class="col-12">
            <div class="alert alert-danger" role="alert">
              <i class="bi bi-exclamation-triangle-fill me-2"></i>
              Error al cargar las vacantes.
            </div>
          </div>
        `;
      }
    }
  }

  // Cargar vacantes en secciones Activas, Vencidas, Cerradas
  function renderJobs(jobs) {
    const activeContainer = document.getElementById("activeJobsList");
    const expiredContainer = document.getElementById("expiredJobsList");
    const closedContainer = document.getElementById("closedJobsList");

    if (!activeContainer || !expiredContainer || !closedContainer) return;

    const activeJobs = jobs.filter((j) => j.status === "active");
    const expiredJobs = jobs.filter((j) => j.status === "expired");
    const closedJobs = jobs.filter((j) => j.status === "closed");

    activeContainer.innerHTML = activeJobs.length
      ? activeJobs.map((job) => createJobCard(job, "active")).join("")
      : '<div class="col-12"><p class="text-muted p-3">No tienes vacantes activas actualmente.</p></div>';

    expiredContainer.innerHTML = expiredJobs.length
      ? expiredJobs.map((job) => createJobCard(job, "expired")).join("")
      : '<div class="col-12"><p class="text-muted p-3">No tienes vacantes vencidas.</p></div>';

    closedContainer.innerHTML = closedJobs.length
      ? closedJobs.map((job) => createJobCard(job, "closed")).join("")
      : '<div class="col-12"><p class="text-muted p-3">No tienes vacantes cerradas.</p></div>';

    attachJobEventListeners();
  }

  // Tarjetas con un poco de información de las vacantes
  function createJobCard(job, status) {
    const skills = job.technical_skills || job.soft_skills || [];
    const statusMap = {
      active: { text: "ACTIVA", color: "bg-success" },
      expired: { text: "VENCIDA", color: "bg-warning text-dark" },
      closed: { text: "CERRADA", color: "bg-secondary" },
    };
    const selectedStatus = statusMap[status] || statusMap.active;

    const isActive = status === "active";
    const isExpired = status === "expired";
    const isClosed = status === "closed";

    // Generar botones según estado
    let buttons = `
    <button class="btn btn-sm btn-outline-secondary view-job-btn" data-id="${job.id}">
      <i class="bi bi-eye"></i> Ver
    </button>
  `;

    if (isActive) {
      buttons += `
      <button class="btn btn-outline-primary btn-sm view-candidates-btn" data-job-id="${job.id}" data-job-title="${job.title}">
        <i class="bi bi-people"></i> Candidatos
      </button>
      <button class="btn btn-outline-danger btn-sm toggle-status-btn" data-job-id="${job.id}" data-action="close">
        <i class="bi bi-x-circle"></i> Cerrar
      </button>
    `;
    }

    if (isExpired) {
      buttons += `
      <button class="btn btn-outline-primary btn-sm view-candidates-btn" data-job-id="${job.id}" data-job-title="${job.title}">
        <i class="bi bi-people"></i> Candidatos
      </button>
      <button class="btn btn-outline-danger btn-sm toggle-status-btn" data-job-id="${job.id}" data-action="close">
        <i class="bi bi-x-circle"></i> Cerrar
      </button>
      <button class="btn btn-outline-success btn-sm toggle-status-btn" data-job-id="${job.id}" data-action="reopen">
        <i class="bi bi-calendar-plus"></i> Reabrir
      </button>
    `;
    }

    if (isClosed) {
      buttons += `
      <button class="btn btn-outline-success btn-sm toggle-status-btn" data-job-id="${job.id}" data-action="reopen">
        <i class="bi bi-arrow-counterclockwise"></i> Reabrir
      </button>
      <button class="btn btn-outline-primary btn-sm view-candidates-btn" data-job-id="${job.id}" data-job-title="${job.title}">
        <i class="bi bi-people"></i> Candidatos
      </button>
    `;
      // El botón de eliminar vacante cerrada solo se muestra si el rol es estrictamente admin
      if (userRole === "admin") {
        buttons += `
        <button class="btn btn-outline-danger btn-sm toggle-status-btn" data-job-id="${job.id}" data-action="delete">
          <i class="bi bi-trash"></i> Archivar
        </button>
      `;
      }
    }

    return `
    <div class="col-md-6 col-lg-4">
      <div class="card h-100 shadow-sm border-0">
        <div class="card-body d-flex flex-column">
          <div class="d-flex justify-content-between align-items-start mb-2">
            <h5 class="card-title text-primary mb-0">${job.title}</h5>
            <span class="badge ${selectedStatus.color}">${selectedStatus.text}</span>
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
            ${buttons}
          </div>
        </div>
      </div>
    </div>
  `;
  }

  // Escuchador de los botones de las tarjetas de las vacantes vistas por el reclutador
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

    // Cerrar / Reabrir / Eliminar Vacante
    document.querySelectorAll(".toggle-status-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const jobId = e.currentTarget.dataset.jobId;
        const action = e.currentTarget.dataset.action;

        if (action === "reopen") {
          const job = currentJobs.find(
            (item) => String(item.id) === String(jobId),
          );
          if (!job) {
            alert("No se encontró la vacante que deseas reabrir.");
            return;
          }

          const mode = job.status === "expired" ? "expired" : "closed";
          // Redirige a publish.html enviando el modo y el id de la vacante
          window.location.href = `publish.html?mode=reopen-${mode}&id=${encodeURIComponent(job.id)}`;
          return;
        }

        if (action === "delete") {
          await deleteClosedJob(jobId);
          return;
        }

        if (action === "close") {
          const confirmed = confirm(
            "¿Estás seguro de que quieres cerrar esta vacante?",
          );
          if (!confirmed) return;
        }

        await toggleJobStatus(jobId, action);
      });
    });
  }

// Función para almacenar/archivar la vacante cerrada (Exclusivo Admin)
  async function deleteClosedJob(jobId) {
    const confirmationMessage =
      "¿Estás seguro de que deseas archivar esta vacante cerrada?\n\n" +
      "La vacante se guardará como plantilla para futuros usos y se eliminarán de forma permanente todas sus postulaciones asociadas.";

    if (!window.confirm(confirmationMessage)) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/store`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "No se pudo almacenar la vacante.");
      }

      alert("Vacante almacenada correctamente y postulaciones asociadas eliminadas.");
      await loadJobs();
    } catch (error) {
      alert(`Error al procesar: ${error.message}`);
    }
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
      modalJobModality.textContent =
        job.modality || job.work_mode || "No especificado";

    const modalJobLocation = document.getElementById("modalJobLocation");
    if (modalJobLocation)
      modalJobLocation.textContent = job.location || "Remoto / No especificada";

    const modalJobDescription = document.getElementById("modalJobDescription");
    if (modalJobDescription)
      modalJobDescription.textContent =
        job.description || "Sin descripción disponible.";

    const modalJobBenefits = document.getElementById("modalJobBenefits");
    if (modalJobBenefits)
      modalJobBenefits.textContent =
        job.benefits || "Sin beneficios especificados.";

    const modalJobDeadline = document.getElementById("modalJobDeadline");
    if (modalJobDeadline) {
      modalJobDeadline.textContent = job.deadline
        ? new Date(job.deadline).toLocaleDateString("es-ES")
        : "Sin fecha límite";
    }

    // --- Formatear Habilidades Técnicas ---
    const technicalSkillsContainer = document.getElementById(
      "modalTechnicalSkills",
    );
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
        if (action === "close") {
          alert("La vacante ha sido cerrada.");
        }
      } else {
        alert("No se pudo cambiar el estado de la vacante.");
      }
    } catch (error) {
      alert("No se pudo cambiar el estado de la vacante.");
    }
  }

  // Carga los candidatos de la vacante
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

      const appsWithResume = await Promise.all(
        applications.map(async (app) => {
          if (!app.resume && app.resume_id) {
            try {
              const res = await fetch(
                `${API_BASE_URL}/resumes/${app.resume_id}`,
                {
                  headers: { Authorization: `Bearer ${token}` },
                },
              );
              if (res.ok) {
                app.resume = await res.json();
              }
            } catch (e) {
              console.error(`Error al cargar un CV`);
            }
          }
          return app;
        }),
      );

      currentCandidateApplications = appsWithResume;
      renderCandidateCards();
    } catch (error) {
      container.innerHTML =
        '<div class="alert alert-danger">Error al cargar la lista de candidatos.</div>';
    }
  }

  // Crea terjetas con información del análisis de matching
  function renderCandidateCards() {
    const container = document.getElementById("candidatesList");
    if (!container) return;
    const sortMode = candidatesSortSelect?.value || "match";
    const applications = [...currentCandidateApplications];

    applications.sort((left, right) => {
      const leftDetails = left.match_details || {};
      const rightDetails = right.match_details || {};
      const leftExact = Number(leftDetails.exact_match?.score ?? -1);
      const rightExact = Number(rightDetails.exact_match?.score ?? -1);
      const leftSemantic = Number(leftDetails.semantic_match?.score ?? -1);
      const rightSemantic = Number(rightDetails.semantic_match?.score ?? -1);

      if (sortMode === "exact") return rightExact - leftExact;
      if (sortMode === "semantic") return rightSemantic - leftSemantic;
      if (sortMode === "other") {
        const exactDifference = leftExact - rightExact;
        if (exactDifference !== 0) return exactDifference;
        return (
          (rightDetails.exact_match?.extra_skills?.length || 0) -
          (leftDetails.exact_match?.extra_skills?.length || 0)
        );
      }
      return Number(right.match_score || 0) - Number(left.match_score || 0);
    });

    container.innerHTML = applications.map(createCandidateCard).join("");
    attachCandidateEventListeners();
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

  function renderSkillList(values, emptyLabel) {
    if (!Array.isArray(values) || values.length === 0) {
      return `<span class="text-muted">${escapeHtml(emptyLabel)}</span>`;
    }
    return values
      .map(
        (value) =>
          `<span class="badge text-bg-light border me-1 mb-1">${escapeHtml(value)}</span>`,
      )
      .join("");
  }

  function formatMatchScore(value) {
    const score = Number(value);
    return Number.isFinite(score)
      ? `${Math.round((score <= 1 ? score * 100 : score) * 100) / 100}%`
      : "No disponible";
  }

  // Crea la tarjeta básica que presenta al candidato postulado y su CV
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
      app.candidate_email || resume.candidate_email || parsed.email || "N/A";

    const professionalTitle =
      parsed.professional_title ||
      parsed.title ||
      parsed.titulo ||
      "Sin título especificado";
    const details = app.match_details || {};
    const exactMatch = details.exact_match || {};
    const semanticMatch = details.semantic_match || {};
    const aiAnalysis = app.ai_analysis || {};
    const overqualification = details.overqualification || {};
    const detailsId = `match-details-${String(app.id).replace(/[^a-zA-Z0-9_-]/g, "")}`;
    const overqualificationId = `overqualification-${String(app.id).replace(/[^a-zA-Z0-9_-]/g, "")}`;
    const matchPros = renderSkillList(
      aiAnalysis.pros,
      "Sin puntos fuertes disponibles.",
    );
    const matchCons = renderSkillList(
      aiAnalysis.cons,
      "Sin riesgos disponibles.",
    );
    const overqualificationRow = (label, flag, reason) => `
      <div class="mb-2">
        <strong>${label}:</strong> ${flag === "YES" ? "SÍ" : "NO"}
        <div class="small text-muted">${escapeHtml(reason || "Sin detalle disponible.")}</div>
      </div>
    `;

    return `
      <div class="card border-0 shadow-sm ${isRejected ? "opacity-50 bg-light" : ""}">
        <div class="card-body d-flex justify-content-between align-items-center">
          <div>
            <h6 class="fw-bold mb-1">${escapeHtml(candidateName)}</h6>
            <p class="text-muted small mb-1">
              <i class="bi bi-envelope"></i> ${escapeHtml(candidateEmail)} |
              <i class="bi bi-briefcase"></i> ${escapeHtml(professionalTitle)}
            </p>
            <span class="badge ${badgeBg}">Match: ${score}%</span>
            ${isRejected ? '<span class="badge bg-secondary ms-1">Descartado</span>' : ""}
          </div>

          <div class="d-flex flex-wrap justify-content-end gap-2">
            <button class="btn btn-outline-info btn-sm view-cv-btn" data-resume-id="${app.resume_id}">
              <i class="bi bi-file-earmark-person"></i> Ver CV
            </button>
            <button class="btn btn-outline-primary btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#${detailsId}" aria-expanded="false" aria-controls="${detailsId}">
              <i class="bi bi-list-check"></i> Detalles del match
            </button>
            ${
              app.is_overqualified === true
                ? `<button class="btn btn-outline-warning btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#${overqualificationId}" aria-expanded="false" aria-controls="${overqualificationId}">
                    <i class="bi bi-exclamation-triangle"></i> Ver sobrecalificado
                  </button>`
                : ""
            }
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
        <div class="collapse border-top" id="${detailsId}">
          <div class="card-body">
            <div class="row g-3">
              <div class="col-md-6">
                <h6>Coincidencia exacta: ${formatMatchScore(exactMatch.score)}</h6>
                <p class="small mb-1"><strong>Habilidades coincidentes</strong></p>
                <div class="mb-2">${renderSkillList(exactMatch.matched_skills, "Ninguna")}</div>
                <p class="small mb-1"><strong>Habilidades faltantes</strong></p>
                <div class="mb-2">${renderSkillList(exactMatch.missing_skills, "Ninguna")}</div>
                <p class="small mb-1"><strong>Otras habilidades</strong></p>
                <div>${renderSkillList(exactMatch.extra_skills, "Ninguna")}</div>
              </div>
              <div class="col-md-6">
                <h6>Coincidencia semántica: ${formatMatchScore(semanticMatch.score)}</h6>
                <h6 class="mt-3">Opinión de IA</h6>
                <p class="small">${escapeHtml(aiAnalysis.opinion || "Análisis no disponible.")}</p>
                <p class="small fw-semibold mb-1">Fortalezas</p>
                <div class="mb-2">${matchPros}</div>
                <p class="small fw-semibold mb-1">Riesgos / contras</p>
                <div>${matchCons}</div>
              </div>
            </div>
          </div>
        </div>
        ${
          app.is_overqualified === true
            ? `<div class="collapse border-top" id="${overqualificationId}">
                <div class="card-body">
                  <h6 class="fw-bold">Señales de sobrecalificación</h6>
                  ${overqualificationRow("Análisis de IA", overqualification.over_ia_analysis, overqualification.details?.ia_reason)}
                  ${overqualificationRow("Tipo de perfil", overqualification.over_profile_type, overqualification.details?.profile_reason)}
                  ${overqualificationRow("Habilidades técnicas", overqualification.over_technical_skills, overqualification.details?.technical_reason)}
                </div>
              </div>`
            : ""
        }
      </div>
    `;
  }

  // Escuchadores
  function attachCandidateEventListeners() {
    // para el botón de Ver CV del candidato postulado
    document.querySelectorAll(".view-cv-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const resumeId = e.currentTarget.dataset.resumeId;
        await loadCVDetail(resumeId);
        if (cvDetailModal) cvDetailModal.show();
      });
    });

    // para el botón de descartar candidato
    document.querySelectorAll(".reject-candidate-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();

        const appId = e.currentTarget.dataset.appId;
        const jobId = e.currentTarget.dataset.jobId;

        const reason = prompt(
          "ADVERTENCIA: El descarte es PERMANENTE. Ingresa el motivo del descarte (opcional):",
        );

        if (reason !== null) {
          await rejectApplication(appId, jobId, reason.trim());
        }
      });
    });
  }

  // Carga la información del CV del candidato
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
      const techSkills =
        resume.extracted_skills ||
        parsed.technical_skills ||
        parsed.skills ||
        [];
      const softSkills = parsed.soft_skills || [];

      const formattedTech = Array.isArray(techSkills)
        ? techSkills.join(", ")
        : techSkills;
      const formattedSoft = Array.isArray(softSkills)
        ? softSkills.join(", ")
        : softSkills;

      const nameElem = document.getElementById("cvCandidateName");
      if (nameElem) {
        nameElem.innerText =
          parsed.full_name || resume.candidate_email || "Perfil de Candidato";
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
      body.innerHTML =
        '<div class="alert alert-danger">Error al cargar el detalle del CV.</div>';
    }
  }

  // Descarta al candidato
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
        },
      );

      if (response.ok) {
        await loadCandidates(jobId);
      } else {
        alert(`No se pudo descartar al candidato.`);
      }
    } catch (error) {}
  }
});