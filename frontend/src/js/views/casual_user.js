//# Subida de CV, filtros de búsqueda y autocompletado con Modales Globales
import { API_BASE_URL } from "../config.js";

document.addEventListener("DOMContentLoaded", () => {
  let allJobs = [];
  let selectedJobId = null;
  let extractedResumeData = null;

  const applyModalElement = document.getElementById("applyModal");
  const applyModal = applyModalElement
    ? new bootstrap.Modal(applyModalElement)
    : null;

  const directApplyModalElement = document.getElementById("directApplyModal");
  const directApplyModal = directApplyModalElement
    ? new bootstrap.Modal(directApplyModalElement)
    : null;

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

  // Ajuste dinámico del Navbar según la sesión iniciada
  setupNavbar();

  // Cargar ofertas al iniciar
  loadPublicJobs();

  // -------------------------------------------------------------
  // Configuración del Buscador en tiempo real
  // -------------------------------------------------------------
  const searchInput = document.getElementById("searchInput");

  const filterJobs = () => {
    const query = (searchInput?.value || "").trim().toLowerCase();
    if (!query) {
      renderJobs(allJobs);
      return;
    }

    const filtered = allJobs.filter((job) => {
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
        .toLowerCase();

      return searchableText.includes(query);
    });

    renderJobs(filtered);
  };

  document.getElementById("searchBtn")?.addEventListener("click", filterJobs);
  searchInput?.addEventListener("input", filterJobs);
  searchInput?.addEventListener("keyup", (e) => {
    if (e.key === "Enter") filterJobs();
  });

  // Evento Paso 1: Subir PDF y Extraer (Solo usuario casual)
  document
    .getElementById("extractCvBtn")
    ?.addEventListener("click", handleExtractCV);

  // Evento Paso 2: Enviar Postulación (Solo usuario casual)
  document
    .getElementById("stepConfirmCV")
    ?.addEventListener("submit", handleSendApplication);

  // Evento Confirmación Postulación Directa (Usuario Registrado)
  document
    .getElementById("confirmDirectApplyBtn")
    ?.addEventListener("click", handleDirectRegisteredApplication);

  applyModalElement?.addEventListener("hidden.bs.modal", resetModal);

  // -------------------------------------------------------------
  // Funciones principales
  // -------------------------------------------------------------

  function setupNavbar() {
    const token = localStorage.getItem("access_token");
    const navAuthSection = document.getElementById("navAuthSection");
    const navCandidateDashboard = document.getElementById(
      "navCandidateDashboard",
    );
    const navRecruiterDashboard = document.getElementById(
      "navRecruiterDashboard",
    );

    if (token) {
      if (navCandidateDashboard) navCandidateDashboard.style.display = "block";
      if (navRecruiterDashboard) navRecruiterDashboard.style.display = "block";

      if (navAuthSection) {
        navAuthSection.innerHTML = `
          <button id="logoutBtn" class="btn btn-outline-light btn-sm">
            <i class="bi bi-box-arrow-right"></i> Salir
          </button>
        `;
        document.getElementById("logoutBtn")?.addEventListener("click", () => {
          localStorage.removeItem("access_token");
          window.location.reload();
        });
      }
    }
  }

  async function loadPublicJobs() {
    const container = document.getElementById("jobsContainer");
    try {
      const response = await fetch(`${API_BASE_URL}/jobs?status=active`, {
        method: "GET",
      });
      if (!response.ok)
        throw new Error(
          "Error al cargar las ofertas. No se pudo acceder a la base de datos.",
        );

      const data = await response.json();
      allJobs = Array.isArray(data) ? data : data.items || [];

      renderJobs(allJobs);
    } catch (error) {
      if (container) {
        container.innerHTML = `
          <div class="col-12">
            <div class="alert alert-danger">No se pudieron cargar las vacantes. Intenta de nuevo más tarde.</div>
          </div>
        `;
      }
    }
  }

  // Muestra las vacantes en la pantalla y algunos de sus datos en tarjetas con botones
  function renderJobs(jobs) {
    const container = document.getElementById("jobsContainer");
    const countBadge = document.getElementById("jobsCount");

    if (countBadge) countBadge.innerText = `${jobs.length} ofertas`;

    if (!container) return;

    if (!jobs.length) {
      container.innerHTML = `
        <div class="col-12 text-center py-5">
          <p class="text-muted fs-5">No se encontraron vacantes disponibles.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = jobs
      .map((job) => {
        const techSkillsHtml = (job.technical_skills || [])
          .slice(0, 4)
          .map(
            (s) => `<span class="badge bg-light text-dark border">${s}</span>`,
          )
          .join("");

        return `
          <div class="col-md-6 col-lg-4 mb-4">
            <div class="card h-100 shadow-sm border-0">
              <div class="card-body d-flex flex-column">
                <h5 class="card-title text-primary fw-bold mb-1">${job.title}</h5>
                <p class="text-muted small mb-2">
                  <i class="bi bi-building"></i> ${job.area || "General"} | 
                  <i class="bi bi-laptop"></i> ${job.modality || "Presencial"}
                </p>
                <p class="card-text text-muted flex-grow-1 text-truncate">${job.description || ""}</p>
                <p class="text-secondary mb-3" style="white-space: pre-line;">${job.benefits || "Sin beneficios especificados."}</p>
                <hr>

                <div class="d-flex flex-wrap gap-1 mb-3">
                  ${techSkillsHtml}
                </div>

                <div class="d-grid gap-2">
                  <button class="btn btn-outline-secondary btn-sm view-job-detail-btn" data-job-id="${job.id}">
                    <i class="bi bi-info-circle"></i> Información
                  </button>
                  <button class="btn btn-primary w-100 open-apply-modal-btn" data-job-id="${job.id}">
                    <i class="bi bi-send"></i> Postularme
                  </button>
                </div>
              </div>
            </div>
          </div>
        `;
      })
      .join("");

    document.querySelectorAll(".view-job-detail-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const jobId = e.currentTarget.dataset.jobId;
        openJobDetailModal(jobId);
      });
    });

    document.querySelectorAll(".open-apply-modal-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const jobId = e.currentTarget.dataset.jobId;
        selectedJobId = jobId;
        const job = allJobs.find((j) => j.id == selectedJobId);
        const token = localStorage.getItem("access_token");

        if (job) {
          // --- FLUJO PARA USUARIO REGISTRADO: POSTULACIÓN DIRECTA SIN FORMULARIO ---
          if (token) {
            const titleEl = document.getElementById("directApplyJobTitle");
            const subtitleEl = document.getElementById(
              "directApplyJobSubtitle",
            );
            if (titleEl) titleEl.innerText = job.title;
            if (subtitleEl)
              subtitleEl.innerText = `${job.area || "General"} • ${job.modality || "Presencial"}`;

            if (directApplyModal) directApplyModal.show();
            return;
          }

          // --- FLUJO PARA USUARIO CASUAL: MANTIENE EL MODAL CON FORMULARIO/PDF ---
          const titleEl = document.getElementById("applyModalJobTitle");
          const subtitleEl = document.getElementById("applyModalJobSubtitle");
          if (titleEl) titleEl.innerText = job.title;
          if (subtitleEl)
            subtitleEl.innerText = `${job.area || ""} • ${job.modality || ""}`;

          if (applyModal) applyModal.show();
          await checkAndPreloadUserResume();
        }
      });
    });
  }

  function openJobDetailModal(jobId) {
    const job = allJobs.find((j) => String(j.id) === String(jobId));
    if (!job) return;

    const titleEl = document.getElementById("modalJobTitle");
    const subtitleEl = document.getElementById("modalJobSubtitle");
    const descriptionEl = document.getElementById("modalJobDescription");
    const benefitsEl = document.getElementById("modalJobBenefits");
    const deadlineEl = document.getElementById("modalJobDeadline");
    const techSkillsEl = document.getElementById("modalTechnicalSkills");
    const softSkillsEl = document.getElementById("modalSoftSkills");

    if (titleEl) titleEl.textContent = job.title || "Sin título";
    if (subtitleEl)
      subtitleEl.textContent = `${job.area || "General"} • ${job.modality || "Presencial"}`;
    if (descriptionEl)
      descriptionEl.textContent =
        job.description || "Sin descripción disponible.";
    if (benefitsEl)
      benefitsEl.textContent = job.benefits || "Sin beneficios especificados.";
    if (deadlineEl)
      deadlineEl.textContent = job.deadline
        ? new Date(job.deadline).toLocaleDateString("es-ES")
        : "Sin fecha límite";

    if (techSkillsEl) {
      const skills = Array.isArray(job.technical_skills)
        ? job.technical_skills
        : [];
      techSkillsEl.innerHTML = skills.length
        ? skills
            .map(
              (skill) =>
                `<span class="badge bg-primary me-1 mb-1">${skill}</span>`,
            )
            .join("")
        : '<span class="text-muted">Ninguna especificada</span>';
    }

    if (softSkillsEl) {
      const skills = Array.isArray(job.soft_skills) ? job.soft_skills : [];
      softSkillsEl.innerHTML = skills.length
        ? skills
            .map(
              (skill) =>
                `<span class="badge bg-secondary me-1 mb-1">${skill}</span>`,
            )
            .join("")
        : '<span class="text-muted">Ninguna especificada</span>';
    }

    const jobDetailModalElement = document.getElementById("jobDetailModal");
    if (jobDetailModalElement) {
      const modal = new bootstrap.Modal(jobDetailModalElement);
      modal.show();
    }
  }

  async function checkAndPreloadUserResume() {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/resumes/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) return;
      const responseData = await response.json();
      if (!responseData) return;

      const data = Array.isArray(responseData) ? responseData[0] : responseData;
      if (!data) return;
      extractedResumeData = data;
    } catch (error) {
    }
  }

  // --- POSTULACIÓN DIRECTA (USUARIO REGISTRADO) ---
  async function handleDirectRegisteredApplication() {
    const token = localStorage.getItem("access_token");
    if (!token || !selectedJobId) {
      await showModalAlert(
        "Sesión Expirada",
        "Por favor inicia sesión nuevamente.",
      );
      window.location.href = "login.html";
      return;
    }

    const confirmBtn = document.getElementById("confirmDirectApplyBtn");
    confirmBtn.disabled = true;
    confirmBtn.innerHTML =
      '<span class="spinner-border spinner-border-sm" role="status"></span> Enviando...';

    try {
      const resumeRes = await fetch(`${API_BASE_URL}/resumes/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!resumeRes.ok) {
        throw new Error(
          "No se encontró un CV asociado a tu cuenta. Por favor sube uno en la sección 'Mi CV'.",
        );
      }

      const resumeDataJson = await resumeRes.json();
      const resumeObj = Array.isArray(resumeDataJson)
        ? resumeDataJson[0]
        : resumeDataJson;

      if (!resumeObj || !resumeObj.id || !resumeObj.candidate_email) {
        throw new Error(
          "Datos de perfil incompletos. Actualiza tu información en 'Mi CV'.",
        );
      }

      const applicationPayload = {
        resume_id: resumeObj.id,
        candidate_email: resumeObj.candidate_email,
      };

      const response = await fetch(
        `${API_BASE_URL}/jobs/${selectedJobId}/applications`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(applicationPayload),
        },
      );

      if (!response.ok) {
        const errData = await response.json();
        let errorMessage = "Error al enviar la postulación.";
        if (typeof errData.detail === "string") {
          errorMessage = errData.detail;
        } else if (Array.isArray(errData.detail)) {
          errorMessage = errData.detail.map((err) => err.msg).join("\n");
        }
        throw new Error(errorMessage);
      }

      // 1. Ocultar el modal de postulación directa antes de mostrar el éxito
      if (directApplyModal) directApplyModal.hide();

      await showModalAlert(
        "¡Éxito!",
        "¡Postulación enviada con éxito! La empresa revisará tu perfil.",
      );

      window.location.href = "candidate/dashboard.html";
    } catch (error) {
      // 2. IMPORTANTE: Ocultar el modal de postulación antes de mostrar el error (ej. límite de 3 alcanzado)
      if (directApplyModal) directApplyModal.hide();
      console.log(error.message);

      await showModalAlert("Error al postularte 1", error.message);
    } finally {
      confirmBtn.disabled = false;
      confirmBtn.innerHTML =
        '<i class="bi bi-send-check me-1"></i> Postularme Ahora';
    }
  }

  async function handleExtractCV() {
    const fileInput = document.getElementById("cvFileInput");
    const extractBtn = document.getElementById("extractCvBtn");
    const aiNotice = document.getElementById("cvAiNotice");
    const file = fileInput?.files[0];

    if (!file) {
      await showModalAlert(
        "Archivo requerido",
        "Por favor selecciona un archivo PDF de tu Hoja de Vida.",
      );
      return;
    }

    if (file.type !== "application/pdf") {
      await showModalAlert(
        "Formato incorrecto",
        "El archivo debe estar estrictamente en formato PDF.",
      );
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    if (extractBtn) extractBtn.disabled = true;
    document.getElementById("extractionSpinner")?.classList.remove("d-none");
    aiNotice?.classList.add("d-none");

    try {
      const response = await fetch(`${API_BASE_URL}/resumes/extract`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Error al procesar el archivo PDF");

      extractedResumeData = await response.json();
      const parsed = extractedResumeData.parsed_data || {};
      if (aiNotice) {
        const aiAvailable =
          extractedResumeData.ai_enrichment_status === "success";
        aiNotice.className = `alert alert-${aiAvailable ? "success" : "warning"} mx-3 mb-3`;
        aiNotice.textContent = aiAvailable
          ? "La IA enriqueció los datos extraídos. Revisa y corrige la información antes de enviar tu postulación."
          : "La IA no está disponible en este momento. Se muestran los datos de extracción automática; puedes revisarlos y completar la información manualmente.";
        aiNotice.setAttribute("role", aiAvailable ? "status" : "alert");
      }

      document.getElementById("candidateFullName").value =
        extractedResumeData.full_name || parsed.full_name || "";
      const emailInput = document.getElementById("candidateEmail");
      if (emailInput && !emailInput.value) {
        emailInput.value = extractedResumeData.email || parsed.email || "";
      }

      document.getElementById("candidateAddress").value =
        extractedResumeData.address || parsed.address || parsed.location || "";
      document.getElementById("candidatePhone").value =
        extractedResumeData.phone || parsed.phone || "";
      document.getElementById("candidateTitle").value =
        extractedResumeData.professional_title ||
        parsed.professional_title ||
        "";

      const techSkillsArr =
        extractedResumeData.technical_skills || parsed.technical_skills || [];
      document.getElementById("candidateSkills").value = Array.isArray(
        techSkillsArr,
      )
        ? techSkillsArr.join(", ")
        : techSkillsArr;

      const softSkillsArr =
        extractedResumeData.soft_skills || parsed.soft_skills || [];
      document.getElementById("candidateSoftSkills").value = Array.isArray(
        softSkillsArr,
      )
        ? softSkillsArr.join(", ")
        : softSkillsArr;

      const moreInfoInput = document.getElementById("candidateMoreInfo");
      if (moreInfoInput) {
        moreInfoInput.value =
          parsed.more_info || extractedResumeData.more_info || "";
      }

      let experienceText = "";
      if (typeof extractedResumeData.work_experience === "string") {
        experienceText = extractedResumeData.work_experience;
      } else if (Array.isArray(extractedResumeData.work_experience)) {
        experienceText = extractedResumeData.work_experience
          .map((exp) =>
            typeof exp === "object"
              ? `${exp.title || exp.role || ""} ${exp.company ? "en " + exp.company : ""}\n${exp.description || ""}`.trim()
              : String(exp),
          )
          .join("\n\n");
      } else if (parsed.work_experience) {
        experienceText = Array.isArray(parsed.work_experience)
          ? parsed.work_experience.join("\n\n")
          : parsed.work_experience;
      } else {
        experienceText = extractedResumeData.raw_text || "";
      }

      document.getElementById("candidateExperience").value =
        experienceText.trim();
      document.getElementById("stepConfirmCV")?.classList.remove("d-none");
    } catch (error) {
      await showModalAlert(
        "Error",
        "Ocurrió un error al procesar el PDF. Revisa el archivo e inténtalo nuevamente.",
      );
    } finally {
      document.getElementById("extractionSpinner")?.classList.add("d-none");
      if (extractBtn) extractBtn.disabled = false;
    }
  }

  // --- ENVÍO FINAL (USUARIO CASUAL) ---
  async function handleSendApplication(e) {
    e.preventDefault();
    const token = localStorage.getItem("access_token");
    if (!selectedJobId) {
      await showModalAlert("Error", "No se identificó la vacante.");
      return;
    }

    const confirmed = await showModalConfirm(
      "Confirmar Postulación",
      "Si ya tenías otro CV, la información se actualizará y cualquier cambio puede afectar tu visibilidad y match en procesos activos.\n\n¿Deseas continuar?",
      "Sí, continuar",
    );
    if (!confirmed) return;

    const skillsInput = document.getElementById("candidateSkills").value;
    const techSkillsList = skillsInput
      ? skillsInput
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
      : [];

    const softSkillsInput = document.getElementById(
      "candidateSoftSkills",
    ).value;
    const softSkillsList = softSkillsInput
      ? softSkillsInput
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
      : [];

    const candidateEmailInput = document.getElementById("candidateEmail");
    const candidateEmail =
      candidateEmailInput?.value.trim().toLowerCase() || "";
    if (!candidateEmail) {
      await showModalAlert(
        "Campo Requerido",
        "Ingresa un correo electrónico para registrar tu postulación.",
      );
      return;
    }

    let safeCandidateEmail = candidateEmail;
    try {
      safeCandidateEmail =
        await window.PluriJobAuth.validateCandidateEmailForCurrentUser(
          candidateEmail,
        );
      if (candidateEmailInput) candidateEmailInput.value = safeCandidateEmail;
    } catch (error) {
      await showModalAlert("Validación", error.message);
      return;
    }

    const submitBtn = document.getElementById("submitApplicationBtn");
    submitBtn.disabled = true;
    submitBtn.innerHTML =
      '<span class="spinner-border spinner-border-sm" role="status"></span> Enviando...';

    try {
      const headers = { "Content-Type": "application/json" };
      let resumeId = null;

      const resumePayload = {
        candidate_email: safeCandidateEmail,
        raw_text: extractedResumeData?.raw_text || "",
        parsed_data: {
          ...(extractedResumeData?.parsed_data || {}),
          full_name: document.getElementById("candidateFullName").value.trim(),
          phone: document.getElementById("candidatePhone").value.trim(),
          address: document.getElementById("candidateAddress").value.trim(),
          professional_title: document
            .getElementById("candidateTitle")
            .value.trim(),
          work_experience: document
            .getElementById("candidateExperience")
            .value.trim(),
          more_info:
            document.getElementById("candidateMoreInfo")?.value.trim() || "",
          technical_skills: techSkillsList,
          soft_skills: softSkillsList,
        },
        extracted_skills: [...new Set([...techSkillsList, ...softSkillsList])],
        file_name:
          document.getElementById("cvFileInput")?.files[0]?.name || null,
      };

      if (resumePayload.work_experience< 50) {
        await showModalAlert(
          "Validación de CV",
          "El texto de la experiencia laboral debe tener al menos 50 caracteres para poder calcular el matching.",
        );
        return;
      }

      const resumeResponse = await fetch(`${API_BASE_URL}/resumes`, {
        method: "POST",
        headers,
        body: JSON.stringify(resumePayload),
      });

      if (!resumeResponse.ok) {
        const errorData = await resumeResponse.json();
        throw new Error(
          typeof errorData.detail === "string"
            ? errorData.detail
            : "No se pudo guardar el CV.",
        );
      }

      const savedResume = await resumeResponse.json();
      resumeId = savedResume.id;

      const applicationPayload = {
        resume_id: resumeId,
        candidate_email: safeCandidateEmail,
      };

      const response = await fetch(
        `${API_BASE_URL}/jobs/${selectedJobId}/applications`,
        {
          method: "POST",
          headers: headers,
          body: JSON.stringify(applicationPayload),
        },
      );

      if (!response.ok) {
        const errData = await response.json();
        let errorMessage = "Error al enviar la postulación.";
        if (typeof errData.detail === "string") errorMessage = errData.detail;
        throw new Error(errorMessage);
      }

      // Ocultar modal casual antes de mostrar la invitación o éxito
      if (applyModal) applyModal.hide();
      showRegisterInvitationModal(candidateEmail);
    } catch (error) {
      // Ocultar el modal de postulación casual antes de mostrar el error
      if (applyModal) applyModal.hide();

      await showModalAlert("Error al postularte 2", error.message);
      console.log(error.message);
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML =
        '<i class="bi bi-send-check"></i> Enviar Postulación';
    }
  }

  function showRegisterInvitationModal(email) {
    const fullName =
      document.getElementById("candidateFullName")?.value.trim() || "";
    const modalHtml = `
      <div class="modal fade" id="registerInviteModal" tabindex="-1" aria-hidden="true" data-bs-backdrop="static">
        <div class="modal-dialog modal-dialog-centered">
          <div class="modal-content text-center p-4">
            <div class="modal-body">
              <div class="mb-3 text-success">
                <i class="bi bi-check-circle-fill display-3"></i>
              </div>
              <h4 class="fw-bold mb-2">¡Postulación Enviada con Éxito!</h4>
              <p class="text-muted small">Hemos recibido tu CV para esta vacante.</p>
              <hr class="my-3">
              <div class="bg-light p-3 rounded mb-3 text-start">
                <h6 class="fw-bold text-primary mb-1">
                  <i class="bi bi-stars me-1"></i> Crea tu cuenta en PluriJob
                </h6>
                <p class="small text-muted mb-0">
                  Regístrate con el correo <strong>${email}</strong> para darle seguimiento en tiempo real al estado de tu postulación.
                </p>
              </div>
              <div class="d-grid gap-2">
                <a href="signup.html?email=${encodeURIComponent(email)}&name=${encodeURIComponent(fullName)}" class="btn btn-primary fw-bold">
                  <i class="bi bi-person-plus-fill me-1"></i> Crear mi cuenta ahora
                </a>
                <button type="button" class="btn btn-link text-muted btn-sm" data-bs-dismiss="modal">
                  Continuar sin registrarme
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    document.getElementById("registerInviteModal")?.remove();
    document.body.insertAdjacentHTML("beforeend", modalHtml);

    const inviteModalElement = document.getElementById("registerInviteModal");
    const inviteModal = new bootstrap.Modal(inviteModalElement);
    inviteModal.show();
  }

  function resetModal() {
    selectedJobId = null;
    extractedResumeData = null;

    document.getElementById("stepUploadCV")?.classList.remove("d-none");
    document.getElementById("extractionSpinner")?.classList.add("d-none");
    document.getElementById("stepConfirmCV")?.classList.add("d-none");

    const cvInput = document.getElementById("cvFileInput");
    if (cvInput) cvInput.value = "";

    document.getElementById("stepConfirmCV")?.reset();
  }
});
