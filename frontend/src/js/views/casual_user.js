//# Subida de CV, filtros de búsqueda
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
      const response = await fetch(`${API_BASE_URL}/jobs`, { method: "GET" });
      if (!response.ok) throw new Error("Error al cargar las ofertas");

      const data = await response.json();
      allJobs = Array.isArray(data) ? data : data.items || [];

      // Filtrar solo las vacantes activas
      allJobs = allJobs.filter((job) => job.status === "active");

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
      <div class="col-md-6 col-lg-4">
        <div class="card h-100 shadow-sm border-0">
          <div class="card-body d-flex flex-column">
            <h5 class="card-title text-primary fw-bold mb-1">${job.title}</h5>
            <p class="text-muted small mb-2">
              <i class="bi bi-building"></i> ${job.area || "General"} | 
              <i class="bi bi-laptop"></i> ${job.modality || "Presencial"}
            </p>
            <p class="card-text text-muted flex-grow-1 text-truncate">${job.description || ""}</p>
            
            <div class="d-flex flex-wrap gap-1 mb-3">
              ${(job.required_skills || [])
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

    // Asignar eventos a los botones de Postularme
    document.querySelectorAll(".open-apply-modal-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        selectedJobId = e.currentTarget.dataset.jobId;
        const job = allJobs.find((j) => j.id == selectedJobId);

        if (job) {
          document.getElementById("modalJobTitle").innerText = job.title;
          document.getElementById("modalJobSubtitle").innerText =
            `${job.area || ""} • ${job.modality || ""}`;
          if (applyModal) applyModal.show();
        }
      });
    });
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
        (j.required_skills &&
          j.required_skills.some((s) => s.toLowerCase().includes(query))),
    );

    renderJobs(filtered);
  }

  // Extracción del CV (PDF)
  async function handleExtractCV() {
    const fileInput = document.getElementById("cvFileInput");
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

    // Ocultar paso 1 y mostrar Spinner
    document.getElementById("stepUploadCV").classList.add("d-none");
    document.getElementById("extractionSpinner").classList.remove("d-none");

    try {
      const response = await fetch(`${API_BASE_URL}/resumes/extract`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Error al procesar el archivo PDF");

      extractedResumeData = await response.json();

      // Rellenar formulario del paso 2 con la información extraída por la IA
      document.getElementById("candidateFullName").value =
        extractedResumeData.full_name || "";
      document.getElementById("candidateEmail").value =
        extractedResumeData.email || "";
      document.getElementById("candidatePhone").value =
        extractedResumeData.phone || "";
      document.getElementById("candidateTitle").value =
        extractedResumeData.professional_title || "";

      const skillsArr =
        extractedResumeData.technical_skills ||
        extractedResumeData.skills ||
        [];
      document.getElementById("candidateSkills").value = skillsArr.join(", ");
      document.getElementById("candidateExperience").value =
        extractedResumeData.work_experience ||
        extractedResumeData.raw_text ||
        "";

      // Mostrar paso 2
      document.getElementById("extractionSpinner").classList.add("d-none");
      document.getElementById("stepConfirmCV").classList.remove("d-none");
    } catch (error) {
      console.error(error);
      alert(
        "Ocurrió un error al procesar el PDF. Revisa el archivo e inténtalo nuevamente.",
      );
      document.getElementById("extractionSpinner").classList.add("d-none");
      document.getElementById("stepUploadCV").classList.remove("d-none");
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
    const skillsList = skillsInput
      ? skillsInput
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
      : [];

    const payload = {
      full_name: document.getElementById("candidateFullName").value,
      email: document.getElementById("candidateEmail").value,
      phone: document.getElementById("candidatePhone").value,
      professional_title: document.getElementById("candidateTitle").value,
      technical_skills: skillsList,
      work_experience: document.getElementById("candidateExperience").value,
      raw_text: extractedResumeData?.raw_text || "",
    };

    const submitBtn = document.getElementById("submitApplicationBtn");
    submitBtn.disabled = true;
    submitBtn.innerHTML =
      '<span class="spinner-border spinner-border-sm" role="status"></span> Enviando...';

    try {
      const token = localStorage.getItem("access_token");
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const response = await fetch(
        `${API_BASE_URL}/jobs/${selectedJobId}/applications`,
        {
          method: "POST",
          headers: headers,
          body: JSON.stringify(payload),
        },
      );

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Error al enviar la postulación.");
      }

      alert("¡Postulación enviada con éxito! La empresa revisará tu perfil.");
      if (applyModal) applyModal.hide();
    } catch (error) {
      console.error(error);
      alert(`Error al postularte: ${error.message}`);
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML =
        '<i class="bi bi-send-check"></i> Enviar Postulación';
    }
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