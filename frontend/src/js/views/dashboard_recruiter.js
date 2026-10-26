//# Dashboard del Reclutador: Gestión de Vacantes y Candidatos con Modales Globales
import { API_BASE_URL } from "../config.js";

document.addEventListener("DOMContentLoaded", async () => {
  const token = localStorage.getItem("access_token");
  const userRole = localStorage.getItem("user_role");

  // Almacén local de vacantes cargadas para acceso rápido
  let currentJobs = [];
  let currentCandidateApplications = [];

  // 1. Verificación de autenticación
  if (!token) {
    window.location.href = "/src/pages/login.html";
    return;
  }

  // -------------------------------------------------------------
  // SISTEMA DE MODALES GLOBALES (Reemplaza alert, confirm y prompt)
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

  function showModalPrompt(title, message) {
    return new Promise((resolve) => {
      document.getElementById("globalAlertTitle").textContent = title;

      const modalBody = document.querySelector("#globalAlertModal .modal-body");
      modalBody.innerHTML = `
        <p class="mb-2 text-dark" style="white-space: pre-line;">${message}</p>
        <input type="text" id="globalPromptInput" class="form-control mt-2" placeholder="Motivo opcional...">
      `;

      const cancelBtn = document.getElementById("globalAlertCancelBtn");
      const confirmBtn = document.getElementById("globalAlertConfirmBtn");

      cancelBtn.style.display = "block";
      cancelBtn.textContent = "Cancelar";
      confirmBtn.textContent = "Descartar Candidato";
      confirmBtn.className = "btn btn-danger px-4";

      const modalElement = document.getElementById("globalAlertModal");
      const modal = new bootstrap.Modal(modalElement);

      let inputValue = null;

      const onConfirm = () => {
        const input = document.getElementById("globalPromptInput");
        inputValue = input ? input.value.trim() : "";
        modal.hide();
      };

      const onCancel = () => {
        inputValue = null;
        modal.hide();
      };

      confirmBtn.onclick = onConfirm;
      cancelBtn.onclick = onCancel;

      const handleHidden = () => {
        confirmBtn.onclick = null;
        cancelBtn.onclick = null;
        // Restaurar HTML original del body del modal por si se usa en otro lado
        modalBody.innerHTML = `<p id="globalAlertMessage" class="mb-0 fs-6 text-dark" style="white-space: pre-line;"></p>`;
        resolve(inputValue);
      };

      modalElement.addEventListener("hidden.bs.modal", handleHidden, {
        once: true,
      });
      modal.show();
    });
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

        await showModalAlert("Éxito", "Reclutador creado correctamente.");
        recruiterForm.reset();
        bootstrap.Modal.getInstance(
          document.getElementById("createRecruiterModal"),
        )?.hide();
      } catch (error) {
        if (errorBox) {
          errorBox.textContent = error.message;
          errorBox.classList.remove("d-none");
        } else {
          await showModalAlert("Error", error.message);
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
          await showModalAlert(
            "Sesión Expirada",
            "Tu sesión ha expirado. Por favor inicia sesión de nuevo.",
          );
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

  function attachJobEventListeners() {
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

    document.querySelectorAll(".view-job-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const jobId = e.currentTarget.getAttribute("data-id");
        openJobModal(jobId);
      });
    });

    document.querySelectorAll(".toggle-status-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const jobId = e.currentTarget.dataset.jobId;
        const action = e.currentTarget.dataset.action;

        if (action === "reopen") {
          const job = currentJobs.find(
            (item) => String(item.id) === String(jobId),
          );
          if (!job) {
            await showModalAlert(
              "Aviso",
              "No se encontró la vacante que deseas reabrir.",
            );
            return;
          }
          openReopenModal(jobId);
          return;
        }

        if (action === "delete") {
          await deleteClosedJob(jobId);
          return;
        }

        if (action === "close") {
          const confirmed = await showModalConfirm(
            "Cerrar Vacante",
            "¿Estás seguro de que quieres cerrar esta vacante?",
            "Sí, cerrar",
          );
          if (!confirmed) return;
        }

        await toggleJobStatus(jobId, action);
      });
    });
  }

  async function deleteClosedJob(jobId) {
    const confirmationMessage =
      "¿Estás seguro de que deseas archivar esta vacante cerrada?\n\n" +
      "La vacante se guardará como plantilla y se eliminarán de forma permanente todas sus postulaciones asociadas.";

    const confirmed = await showModalConfirm(
      "Archivar Vacante",
      confirmationMessage,
      "Sí, archivar",
    );
    if (!confirmed) return;

    try {
      const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/store`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "No se pudo almacenar la vacante.");
      }

      await showModalAlert(
        "Éxito",
        "Vacante almacenada correctamente y postulaciones asociadas eliminadas.",
      );
      await loadJobs();
    } catch (error) {
      await showModalAlert("Error", `Error al procesar: ${error.message}`);
    }
  }

  function openJobModal(jobId) {
    const job = currentJobs.find((j) => String(j.id) === String(jobId));

    if (!job) {
      showModalAlert(
        "Aviso",
        "No se encontró información detallada de esta vacante.",
      );
      return;
    }

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
          await showModalAlert("Éxito", "La vacante ha sido cerrada.");
        }
      } else {
        await showModalAlert(
          "Error",
          "No se pudo cambiar el estado de la vacante.",
        );
      }
    } catch (error) {
      await showModalAlert(
        "Error",
        "No se pudo cambiar el estado de la vacante.",
      );
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
            } catch (e) {}
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

  function attachCandidateEventListeners() {
    // 1. Ver Detalle del CV (Dispara también la notificación automática de "CV visto" / under_review)
    document.querySelectorAll(".view-cv-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const resumeId = e.currentTarget.dataset.resumeId;
        const appId = e.currentTarget.dataset.appId;

        // Notificar al backend que el CV ha sido visto para cambiar estado y enviar correo si aplica
        if (appId) {
          try {
            await fetch(`${API_BASE_URL}/applications/${appId}/view`, {
              method: "PATCH",
              headers: { Authorization: `Bearer ${token}` },
            });
          } catch (err) {
            console.error("No se pudo registrar la visualización del CV", err);
          }
        }

        await loadCVDetail(resumeId);
        if (cvDetailModal) cvDetailModal.show();
      });
    });

    // 2. Cambio de Estado Dinámico (Programar Entrevista -> Contratar) usando #changeApplicationState
    document.querySelectorAll(".change-state-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();
        const appId = e.currentTarget.dataset.appId;
        const jobId = e.currentTarget.dataset.jobId;
        const nextAction = e.currentTarget.dataset.nextAction; // 'interview' o 'hire'

        let title = "Programar Entrevista";
        let message =
          "¿Estás seguro de avanzar este candidato a la etapa de entrevista? Se le notificará por correo electrónico.";
        let confirmText = "Sí, programar";

        if (nextAction === "hire") {
          title = "Contratar Candidato";
          message =
            "¡Atención! Al contratar a este candidato, la vacante se cerrará en automático y se notificará a los demás postulantes. Los demás registros se mantendrán vigentes durante el periodo de prueba.\n\n¿Deseas continuar?";
          confirmText = "Sí, contratar";
        }

        const confirmed = await showModalConfirm(title, message, confirmText);
        if (!confirmed) return;

        try {
          const response = await fetch(
            `${API_BASE_URL}/applications/${appId}/${nextAction}`,
            {
              method: "PATCH",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
              },
            },
          );

          if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(
              errData.detail ||
                "No se pudo actualizar el estado de la postulación.",
            );
          }

          await showModalAlert(
            "Éxito",
            nextAction === "hire"
              ? "¡Candidato contratado y vacante cerrada con éxito!"
              : "Entrevista programada y correo enviado correctamente.",
          );
          await loadCandidates(jobId);
          await loadJobs(); // Refrescar vacantes por si se cerró alguna
        } catch (error) {
          await showModalAlert("Error", error.message);
        }
      });
    });

    // 3. Descartar Candidato
    document.querySelectorAll(".reject-candidate-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();
        const appId = e.currentTarget.dataset.appId;
        const jobId = e.currentTarget.dataset.jobId;

        const reason = await showModalPrompt(
          "Descartar Candidato",
          "ADVERTENCIA: El descarte es PERMANENTE.\nIngresa el motivo del descarte (opcional):",
        );

        if (reason !== null) {
          await rejectApplication(appId, jobId, reason.trim());
        }
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

  // --- RENDERIZADO DE TARJETAS DE CANDIDATOS ---
  function createCandidateCard(app) {
    const score = Math.round(app.match_score || 0);
    let badgeBg = "bg-danger";
    if (score >= 85) badgeBg = "bg-success";
    else if (score >= 70) badgeBg = "bg-primary";
    else if (score >= 60) badgeBg = "bg-warning text-dark";

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

    const appIdStr = String(app.id);
    const detailsId = `match-details-${appIdStr.replace(/[^a-zA-Z0-9_-]/g, "")}`;
    const overqualificationId = `overqualification-${appIdStr.replace(/[^a-zA-Z0-9_-]/g, "")}`;

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

    // Configuración dinámica del botón de estado según el estado actual de la postulación
    let stateBtnText = "Programar Entrevista";
    let stateBtnClass = "btn-outline-primary";
    let targetActionState = "interview";

    if (app.status === "interview_scheduled") {
      stateBtnText = "Contratar";
      stateBtnClass = "btn-outline-success";
      targetActionState = "hire";
    } else if (app.status === "hired") {
      stateBtnText = "Contratado";
      stateBtnClass = "btn-success disabled";
      targetActionState = "none";
    }

    return `
      <div class="card mb-3 shadow-sm border-0">
        <div class="card-body">
          <div class="row align-items-center">
            <div class="col-md-4">
              <h5 class="mb-1 text-dark fw-bold">${escapeHtml(candidateName)}</h5>
              <p class="text-muted small mb-1"><i class="bi bi-briefcase me-1"></i>${escapeHtml(professionalTitle)}</p>
              <p class="text-muted small mb-0"><i class="bi bi-envelope me-1"></i>${escapeHtml(candidateEmail)}</p>
            </div>
            <div class="col-md-3 text-center">
              <span class="badge ${badgeBg} fs-6 px-3 py-2">Match: ${score}%</span>
              <div class="small text-muted mt-1">Estado: <strong>${escapeHtml(app.status)}</strong></div>
            </div>
            <div class="col-md-5 text-md-end mt-3 mt-md-0">
              <!-- Botón Detalles del Match -->
              <button class="btn btn-sm btn-outline-info me-1" type="button" data-bs-toggle="collapse" data-bs-target="#${detailsId}" aria-expanded="false" aria-controls="${detailsId}">
                <i class="bi bi-info-circle"></i> Detalles
              </button>

              <!-- Botón condicional de Sobrecalificación (Sólo aparece si app.is_overqualified es true) -->
              ${
                app.is_overqualified === true
                  ? `<button class="btn btn-sm btn-outline-warning me-1" type="button" data-bs-toggle="collapse" data-bs-target="#${overqualificationId}" aria-expanded="false" aria-controls="${overqualificationId}">
                       <i class="bi bi-exclamation-triangle"></i> Sobrecalificado
                     </button>`
                  : ""
              }

              <button class="btn btn-sm btn-outline-secondary view-cv-btn me-1" data-resume-id="${resume.id || app.resume_id}" data-app-id="${app.id}">
                <i class="bi bi-file-earmark-text"></i> Ver CV
              </button>

              ${
                targetActionState !== "none"
                  ? `<button class="btn btn-sm ${stateBtnClass} change-state-btn me-1" id="changeApplicationState" data-app-id="${app.id}" data-job-id="${app.job_id}" data-next-action="${targetActionState}">
                       <i class="bi bi-check2-circle"></i> ${stateBtnText}
                     </button>`
                  : `<button class="btn btn-sm btn-success me-1 disabled"><i class="bi bi-check-all"></i> Contratado</button>`
              }

              <button class="btn btn-sm btn-outline-danger reject-candidate-btn" data-app-id="${app.id}" data-job-id="${app.job_id}">
                <i class="bi bi-x-circle"></i> Descartar
              </button>
            </div>
          </div>
        </div>

        <!-- Panel Colapsable de Detalles del Match -->
        <div class="collapse border-top" id="${detailsId}">
          <div class="card-body bg-light">
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

        <!-- Panel Colapsable de Sobrecalificación -->
        ${
          app.is_overqualified === true
            ? `<div class="collapse border-top bg-warning-subtle" id="${overqualificationId}">
                 <div class="card-body">
                   <h6 class="fw-bold text-dark mb-3"><i class="bi bi-exclamation-triangle-fill text-warning me-2"></i>Señales de sobrecalificación detectadas</h6>
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
        <h6><strong>Título Profesional:</strong> ${escapeHtml(parsed.professional_title || "N/A")}</h6>
        <p><strong>Domicilio:</strong> ${escapeHtml(parsed.address || "N/A")} | <strong>Teléfono:</strong> ${escapeHtml(parsed.phone || "N/A")}</p>
        <hr>
        <h6><strong>Habilidades Técnicas:</strong></h6>
        <p>${escapeHtml(formattedTech || "Sin especificar")}</p>
        <h6><strong>Habilidades Blandas:</strong></h6>
        <p>${escapeHtml(formattedSoft || "Sin especificar")}</p>
        <hr>
        <h6><strong>Experiencia Laboral:</strong></h6>
        <p style="white-space: pre-line;">${escapeHtml(parsed.work_experience || parsed.summary || "Sin experiencia registrada.")}</p>
        <h6><strong>Más información</strong></h6>
        <p style="white-space: pre-line;">${escapeHtml(parsed.more_info || "Sin información adicional.")}</p>
      `;
    } catch (error) {
      body.innerHTML =
        '<div class="alert alert-danger">Error al cargar el detalle del CV.</div>';
    }
  }

  async function rejectApplication(appId, jobId, rejectionReason = "") {
    const token = localStorage.getItem("access_token");
    if (!token) {
      await showModalAlert(
        "Sesión no válida",
        "Por favor inicia sesión de nuevo.",
      );
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
        await showModalAlert(
          "Descartado",
          "El candidato ha sido descartado y notificado.",
        );
        await loadCandidates(jobId);
      } else {
        const errData = await response.json().catch(() => ({}));
        await showModalAlert(
          "Error",
          errData.detail || "No se pudo descartar al candidato.",
        );
      }
    } catch (error) {
      await showModalAlert(
        "Error",
        "Ocurrió un error al procesar el descarte.",
      );
    }
  }

  // Instancia del modal de reapertura
  const reopenModalElement = document.getElementById("reopenJobModal");
  const reopenModal = reopenModalElement
    ? new bootstrap.Modal(reopenModalElement)
    : null;

  function openReopenModal(jobId) {
    const jobIdInput = document.getElementById("reopenJobId");
    const deadlineInput = document.getElementById("reopenDeadline");
    const errorBox = document.getElementById("reopenErrorBox");

    if (jobIdInput) jobIdInput.value = jobId;
    if (deadlineInput) deadlineInput.value = "";
    if (errorBox) {
      errorBox.textContent = "";
      errorBox.classList.add("d-none");
    }

    if (reopenModal) reopenModal.show();
  }

  const confirmReopenBtn = document.getElementById("confirmReopenBtn");
  if (confirmReopenBtn) {
    confirmReopenBtn.addEventListener("click", async () => {
      const jobId = document.getElementById("reopenJobId")?.value;
      const deadlineVal = document.getElementById("reopenDeadline")?.value;
      const errorBox = document.getElementById("reopenErrorBox");

      if (errorBox) {
        errorBox.textContent = "";
        errorBox.classList.add("d-none");
      }

      const deadlineIso = deadlineVal
        ? new Date(deadlineVal).toISOString()
        : null;

      try {
        const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/reopen`, {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ deadline: deadlineIso }),
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
          throw new Error(data.detail || "No se pudo reabrir la vacante.");
        }

        if (reopenModal) reopenModal.hide();
        await showModalAlert("Éxito", "Vacante reabierta correctamente.");
        await loadJobs();
      } catch (error) {
        if (errorBox) {
          errorBox.textContent = error.message;
          errorBox.classList.remove("d-none");
        } else {
          await showModalAlert("Error", error.message);
        }
      }
    });
  }
});