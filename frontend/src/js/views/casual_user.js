//# Subida de CV, filtros de búsqueda y autocompletado para usuarios autenticados
import { API_BASE_URL } from "../config.js";

document.addEventListener("DOMContentLoaded", () => {
  let allJobs = [];
  let selectedJobId = null;
  let extractedResumeData = null;

  const applyModalElement = document.getElementById("applyModal");
  const applyModal = applyModalElement
    ? new bootstrap.Modal(applyModalElement)
    : null;

  // Ajuste dinámico del Navbar según la sesión iniciada
  setupNavbar();

  // Cargar ofertas al iniciar
  loadPublicJobs();

  // Búsqueda en vivo
  document.getElementById("searchBtn")?.addEventListener("click", filterJobs);
  document.getElementById("searchInput")?.addEventListener("keyup", (e) => {
    if (e.key === "Enter") filterJobs();
  });

  // Evento Paso 1: Subir PDF y Extraer
  document
    .getElementById("extractCvBtn")
    ?.addEventListener("click", handleExtractCV);

  // Evento Paso 2: Enviar Postulación
  document
    .getElementById("stepConfirmCV")
    ?.addEventListener("submit", handleSendApplication);

  // Reajustar modal al cerrarse
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
      if (!response.ok) throw new Error("Error al cargar las ofertas");

      const data = await response.json();
      allJobs = Array.isArray(data) ? data : data.items || [];

      renderJobs(allJobs);
    } catch (error) {
      console.error(error);
      if (container) {
        container.innerHTML = `
          <div class="col-12">
            <div class="alert alert-danger">No se pudieron cargar las vacantes. Intenta de nuevo más tarde.</div>
          </div>
        `;
      }
    }
  }

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
      .map(
        (job) => `
      <div class="col-md-6 col-lg-4 mb-4">
        <div class="card h-100 shadow-sm border-0">
          <div class="card-body d-flex flex-column">
            <h5 class="card-title text-primary fw-bold mb-1">${job.title}</h5>
            <p class="text-muted small mb-2">
              <i class="bi bi-building"></i> ${job.area || "General"} | 
              <i class="bi bi-laptop"></i> ${job.modality || "Presencial"}
            </p>
            <p class="card-text text-muted flex-grow-1 text-truncate">${job.description || ""}</p>
            
            <div class="d-flex flex-wrap gap-1 mb-3">
              ${(job.technical_skills || [])
                .slice(0, 4)
                .map(
                  (s) =>
                    `<span class="badge bg-light text-dark border">${s}</span>`,
                )
                .join("")}
            </div>

            <button class="btn btn-primary w-100 open-apply-modal-btn" data-job-id="${job.id}">
              <i class="bi bi-send"></i> Postularme
            </button>
          </div>
        </div>
      </div>
    `,
      )
      .join("");

    // Eventos en botones Postularme
    document.querySelectorAll(".open-apply-modal-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        selectedJobId = e.currentTarget.dataset.jobId;
        const job = allJobs.find((j) => j.id == selectedJobId);

        if (job) {
          document.getElementById("modalJobTitle").innerText = job.title;
          document.getElementById("modalJobSubtitle").innerText =
            `${job.area || ""} • ${job.modality || ""}`;

          // Mostrar modal primero
          if (applyModal) applyModal.show();

          // Verificar si el usuario ya está autenticado para autocompletar su CV
          await checkAndPreloadUserResume();
        }
      });
    });
  }

  // Cargar datos preexistentes del CV si hay sesión activa
  async function checkAndPreloadUserResume() {
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
      if (!responseData) return;

      // Obtener el registro principal
      const data = Array.isArray(responseData) ? responseData[0] : responseData;
      if (!data) return;

      extractedResumeData = data;
      const parsed = data.parsed_data || {};

      // Poblar directamente el formulario con la información de la DB
      document.getElementById("candidateFullName").value =
        parsed.full_name || "";

      const emailInput = document.getElementById("candidateEmail");
      if (emailInput) {
        emailInput.value = data.candidate_email || parsed.email || "";
      }

      const addressInput = document.getElementById("candidateAddress");
      if (addressInput) {
        addressInput.value = parsed.address || parsed.location || data.address || "";
      }

      document.getElementById("candidatePhone").value = parsed.phone || "";
      document.getElementById("candidateTitle").value =
        parsed.professional_title || "";

      // Habilidades
      const techSkills = parsed.technical_skills || data.extracted_skills || [];
      const softSkills = parsed.soft_skills || [];

      document.getElementById("candidateSkills").value = Array.isArray(
        techSkills,
      )
        ? techSkills.join(", ")
        : techSkills;

      document.getElementById("candidateSoftSkills").value = Array.isArray(
        softSkills,
      )
        ? softSkills.join(", ")
        : softSkills;

      // Información extra / no clasificada (Añadido)
      const moreInfoInput = document.getElementById("candidateMoreInfo");
      if (moreInfoInput) {
        moreInfoInput.value = parsed.more_info || data.more_info || "";
      }

      // Experiencia
      let expValue = parsed.work_experience || data.work_experience || "";
      if (Array.isArray(expValue)) {
        expValue = expValue.join("\n\n");
      }
      document.getElementById("candidateExperience").value = expValue;

      // Ocultar sección de subir archivo y mostrar formulario listo
      document.getElementById("stepUploadCV")?.classList.add("d-none");
      document.getElementById("stepConfirmCV")?.classList.remove("d-none");
    } catch (error) {
      console.error("Error al precargar la información del CV:", error);
    }
  }

  function filterJobs() {
    const query = document
      .getElementById("searchInput")
      ?.value.toLowerCase()
      .trim();
    if (!query) {
      renderJobs(allJobs);
      return;
    }

    const filtered = allJobs.filter(
      (j) =>
        j.title.toLowerCase().includes(query) ||
        (j.description && j.description.toLowerCase().includes(query)) ||
        (j.area && j.area.toLowerCase().includes(query)) ||
        (j.technical_skills &&
          j.technical_skills.some((s) => s.toLowerCase().includes(query))),
    );

    renderJobs(filtered);
  }

  // Extracción del CV (PDF) para usuarios sin sesión / anónimos
  async function handleExtractCV() {
    const fileInput = document.getElementById("cvFileInput");
    const extractBtn = document.getElementById("extractCvBtn");
    const file = fileInput?.files[0];

    if (!file) {
      alert("Por favor selecciona un archivo PDF de tu Hoja de Vida.");
      return;
    }

    if (file.type !== "application/pdf") {
      alert("El archivo debe estar en formato PDF.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    if (extractBtn) extractBtn.disabled = true;
    document.getElementById("extractionSpinner")?.classList.remove("d-none");

    try {
      const response = await fetch(`${API_BASE_URL}/resumes/extract`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Error al procesar el archivo PDF");

      extractedResumeData = await response.json();

      document.getElementById("candidateFullName").value =
        extractedResumeData.full_name || extractedResumeData.parsed_data?.full_name || "";

      const emailInput = document.getElementById("candidateEmail");
      if (emailInput && !emailInput.value) {
        emailInput.value = extractedResumeData.email || extractedResumeData.parsed_data?.email || "";
      }

      document.getElementById("candidateAddress").value =
        extractedResumeData.address || extractedResumeData.parsed_data?.address || "";

      document.getElementById("candidatePhone").value =
        extractedResumeData.phone || extractedResumeData.parsed_data?.phone || "";
      document.getElementById("candidateTitle").value =
        extractedResumeData.professional_title || extractedResumeData.parsed_data?.professional_title || "";

      const techSkillsArr = extractedResumeData.technical_skills || extractedResumeData.parsed_data?.technical_skills || [];
      document.getElementById("candidateSkills").value =
        Array.isArray(techSkillsArr) ? techSkillsArr.join(", ") : techSkillsArr;

      const softSkillsArr = extractedResumeData.soft_skills || extractedResumeData.parsed_data?.soft_skills || [];
      document.getElementById("candidateSoftSkills").value =
        Array.isArray(softSkillsArr) ? softSkillsArr.join(", ") : softSkillsArr;

      // Asignar more_info buscando en la raíz o en parsed_data (Ajuste clave)
      const moreInfoInput = document.getElementById("candidateMoreInfo");
      if (moreInfoInput) {
        moreInfoInput.value =
          extractedResumeData.parsed_data?.more_info || extractedResumeData.more_info || "";
      }

      let experienceText = "";
      if (typeof extractedResumeData.work_experience === "string") {
        experienceText = extractedResumeData.work_experience;
      } else if (Array.isArray(extractedResumeData.work_experience)) {
        experienceText = extractedResumeData.work_experience
          .map((exp) => {
            if (typeof exp === "object") {
              return `${exp.title || exp.role || ""} ${exp.company ? "en " + exp.company : ""}\n${exp.description || ""}`.trim();
            }
            return String(exp);
          })
          .join("\n\n");
      } else if (extractedResumeData.parsed_data?.summary) {
        experienceText = extractedResumeData.parsed_data.summary;
      } else {
        experienceText = extractedResumeData.raw_text || "";
      }

      document.getElementById("candidateExperience").value =
        experienceText.trim();

      document.getElementById("stepConfirmCV")?.classList.remove("d-none");
    } catch (error) {
      console.error(error);
      alert(
        "Ocurrió un error al procesar el PDF. Revisa el archivo e inténtalo nuevamente.",
      );
    } finally {
      document.getElementById("extractionSpinner")?.classList.add("d-none");
      if (extractBtn) extractBtn.disabled = false;
    }
  }

  // Envío final de la postulación
  async function handleSendApplication(e) {
    e.preventDefault();

    if (!selectedJobId) {
      alert("Error: No se identificó la vacante.");
      return;
    }

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
    const candidateEmail = candidateEmailInput?.value.trim().toLowerCase() || "";
    if (!candidateEmail) {
      alert("Ingresa un correo electrónico para registrar tu postulación.");
      return;
    }

    let safeCandidateEmail = candidateEmail;
    try {
      safeCandidateEmail = await window.PluriJobAuth.validateCandidateEmailForCurrentUser(
        candidateEmail,
      );
      if (candidateEmailInput) candidateEmailInput.value = safeCandidateEmail;
    } catch (error) {
      alert(error.message);
      return;
    }

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
        more_info: document.getElementById("candidateMoreInfo")?.value.trim() || "",
        technical_skills: techSkillsList,
        soft_skills: softSkillsList,
      },
      extracted_skills: [...new Set([...techSkillsList, ...softSkillsList])],
      file_name: document.getElementById("cvFileInput")?.files[0]?.name || null,
    };

    const submitBtn = document.getElementById("submitApplicationBtn");
    submitBtn.disabled = true;
    submitBtn.innerHTML =
      '<span class="spinner-border spinner-border-sm" role="status"></span> Enviando...';

    try {
      const token = localStorage.getItem("access_token");
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

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

      const applicationPayload = {
        resume_id: savedResume.id,
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
        if (Array.isArray(errData.detail)) {
          errorMessage = errData.detail
            .map((err) => `${err.loc.join(".")}: ${err.msg}`)
            .join("\n");
        } else if (typeof errData.detail === "string") {
          errorMessage = errData.detail;
        }

        throw new Error(errorMessage);
      }

      // Ocultar el modal de postulación actual
      if (applyModal) applyModal.hide();

      // Validar si el usuario está registrado o no
      if (!token) {
        // Usuario anónimo / casual -> Desplegar invitación a registrarse
        showRegisterInvitationModal(candidateEmail);
      } else {
        // Usuario autenticado
        alert("¡Postulación enviada con éxito! La empresa revisará tu perfil.");
      }
    } catch (error) {
      console.error("Detalle del error:", error);
      alert(`Error al postularte:\n${error.message}`);
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML =
        '<i class="bi bi-send-check"></i> Enviar Postulación';
    }
  }

  // Genera y despliega el modal de invitación al registro
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
              <p class="text-muted small">
                Hemos recibido tu CV para esta vacante.
              </p>
              <hr class="my-3">
              <div class="bg-light p-3 rounded mb-3 text-start">
                <h6 class="fw-bold text-primary mb-1">
                  <i class="bi bi-stars me-1"></i> Crea tu cuenta en PluriJob
                </h6>
                <p class="small text-muted mb-0">
                  Regístrate con el correo <strong>${email}</strong> para darle seguimiento en tiempo real al estado de tu postulación y consultar el desglose de tu <strong>Match %</strong>.
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