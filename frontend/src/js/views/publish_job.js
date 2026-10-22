import { API_BASE_URL } from "../config.js";

document.addEventListener("DOMContentLoaded", async () => {
  const jobForm = document.getElementById("publishJobForm");
  if (!jobForm) return;

  const params = new URLSearchParams(window.location.search);
  const modeParam = params.get("mode");
  const jobIdParam = params.get("id");
  const token = localStorage.getItem("access_token");

  if (!token) {
    alert("Debes iniciar sesión para publicar o reabrir una vacante.");
    window.location.href = "/login.html";
    return;
  }

  // Referencias a contenedores de interfaz
  const modeSelectionContainer = document.getElementById(
    "modeSelectionContainer",
  );
  const workspaceContainer = document.getElementById("workspaceContainer");
  const quickSwitchSidebar = document.getElementById("quickSwitchSidebar");
  const mainWorkspaceCol = document.getElementById("mainWorkspaceCol");
  const templatesSection = document.getElementById("templatesSection");
  const formAndAiWorkspace = document.getElementById("formAndAiWorkspace");
  const aiDraftSection = document.getElementById("aiDraftSection");
  const formHeaderTitle = document.getElementById("formHeaderTitle");

  const aiInstruction = document.getElementById("aiJobInstruction");
  const generateDraftButton = document.getElementById("generateJobDraftButton");
  const aiNotice = document.getElementById("jobAiNotice");
  const submitButton = jobForm.querySelector('button[type="submit"]');
  const resetButton = jobForm.querySelector('button[type="reset"]');

  let selectedTemplateIdForModal = null;
  let currentStoredJobs = [];

  const fields = {
    title: document.getElementById("jobTitle"),
    area: document.getElementById("jobArea"),
    profileType: document.getElementById("profileType"),
    modality: document.getElementById("jobModality"),
    location: document.getElementById("jobLocation"),
    description: document.getElementById("jobDescription"),
    benefits: document.getElementById("jobBenefits"),
    technicalSkills: document.getElementById("technicalSkills"),
    softSkills: document.getElementById("softSkills"),
    deadline: document.getElementById("jobDeadline"),
  };

  // Función auxiliar de escape HTML
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

  // Función para activar una vista (manual, template, ai)
  async function switchViewMode(targetMode) {
    if (modeSelectionContainer) modeSelectionContainer.classList.add("d-none");
    if (workspaceContainer) workspaceContainer.classList.remove("d-none");
    if (quickSwitchSidebar) quickSwitchSidebar.classList.remove("d-none");

    // Ajustar columnas principales para dejar espacio a la barra lateral izquierda
    if (mainWorkspaceCol) mainWorkspaceCol.className = "col-lg-9";

    // Ocultar ambas secciones internas por defecto
    if (templatesSection) templatesSection.classList.add("d-none");
    if (formAndAiWorkspace) formAndAiWorkspace.classList.add("d-none");
    if (aiDraftSection) aiDraftSection.classList.add("d-none");

    if (targetMode === "manual") {
      if (formAndAiWorkspace) formAndAiWorkspace.classList.remove("d-none");
      if (formHeaderTitle) {
        formHeaderTitle.innerHTML =
          '<i class="bi bi-file-earmark-text-fill me-2"></i>Redactar Nueva Vacante';
      }
      jobForm.reset();
    } else if (targetMode === "ai") {
      if (formAndAiWorkspace) formAndAiWorkspace.classList.remove("d-none");
      if (aiDraftSection) aiDraftSection.classList.remove("d-none");
      if (formHeaderTitle) {
        formHeaderTitle.innerHTML =
          '<i class="bi bi-stars me-2"></i>Generar Vacante con IA';
      }
    } else if (targetMode === "template") {
      if (templatesSection) templatesSection.classList.remove("d-none");
      await loadStoredTemplates();
    }
  }

  // Delegación de eventos robusta para las opciones iniciales
  if (modeSelectionContainer) {
    modeSelectionContainer.addEventListener("click", (e) => {
      const cardOrBtn = e.target.closest("[data-mode]");
      if (!cardOrBtn) return;

      const mode = cardOrBtn.dataset.mode;
      if (mode) {
        switchViewMode(mode);
      }
    });
  }

  // Event Listeners para los botones de la barra lateral izquierda
  document.querySelectorAll(".switch-mode-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const mode = btn.dataset.mode;
      switchViewMode(mode);
    });
  });

  // Botones de retorno al menú principal
  document
    .getElementById("backToSelectionBtn")
    ?.addEventListener("click", resetToMenu);
  document
    .getElementById("backToSelectionFormBtn")
    ?.addEventListener("click", resetToMenu);

  function resetToMenu() {
    if (workspaceContainer) workspaceContainer.classList.add("d-none");
    if (quickSwitchSidebar) quickSwitchSidebar.classList.add("d-none");
    if (modeSelectionContainer)
      modeSelectionContainer.classList.remove("d-none");
    jobForm.reset();
  }

  // Cargar vacantes almacenadas (status = "stored") para usarlas como plantilla
  async function loadStoredTemplates() {
    const listContainer = document.getElementById("templatesCardsList");
    if (!listContainer) return;

    listContainer.innerHTML = `
      <div class="text-center py-4">
        <div class="spinner-border text-success" role="status"></div>
        <p class="mt-2 text-muted">Cargando plantillas guardadas...</p>
      </div>
    `;

    try {
      const response = await fetch(`${API_BASE_URL}/jobs`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok)
        throw new Error("No se pudieron cargar las plantillas.");

      const data = await response.json();
      currentStoredJobs = Array.isArray(data) ? data : data.items || [];

      if (!currentStoredJobs.length) {
        listContainer.innerHTML = `
          <div class="col-12">
            <div class="alert alert-info text-center">No hay vacantes almacenadas como plantilla actualmente. Cuando archives vacantes cerradas, aparecerán aquí.</div>
          </div>
        `;
        return;
      }

      listContainer.innerHTML = currentStoredJobs
        .map((job) => {
          const skills = [
            ...(job.technical_skills || []),
            ...(job.soft_skills || []),
          ];
          return `
          <div class="col-md-6">
            <div class="card h-100 shadow-sm border">
              <div class="card-body d-flex flex-column">
                <h5 class="card-title text-success fw-bold">${escapeHtml(job.title)}</h5>
                <p class="text-muted small mb-2">
                  <i class="bi bi-building"></i> ${escapeHtml(job.area || "N/A")} | 
                  <i class="bi bi-laptop"></i> ${escapeHtml(job.modality || "N/A")}
                </p>
                <p class="card-text text-truncate small mb-3">${escapeHtml(job.description || "")}</p>
                
                <div class="d-flex flex-wrap gap-1 mb-3">
                  ${skills
                    .slice(0, 3)
                    .map(
                      (s) =>
                        `<span class="badge bg-light text-dark border">${escapeHtml(s)}</span>`,
                    )
                    .join("")}
                </div>

                <div class="mt-auto d-flex justify-content-end gap-2 pt-2 border-top">
                  <button type="button" class="btn btn-sm btn-outline-secondary view-template-btn" data-id="${job.id}">
                    <i class="bi bi-eye"></i> Ver
                  </button>
                  <button type="button" class="btn btn-sm btn-success select-template-btn" data-id="${job.id}">
                    <i class="bi bi-check2-circle"></i> Seleccionar
                  </button>
                </div>
              </div>
            </div>
          </div>
        `;
        })
        .join("");

      attachTemplateEventListeners();
    } catch (error) {
      listContainer.innerHTML = `<div class="col-12"><div class="alert alert-danger">Error al cargar las plantillas.</div></div>`;
    }
  }

  function attachTemplateEventListeners() {
    document.querySelectorAll(".view-template-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const jobId = e.currentTarget.dataset.id;
        const job = currentStoredJobs.find(
          (j) => String(j.id) === String(jobId),
        );
        if (!job) return;

        selectedTemplateIdForModal = job.id;
        const modalBody = document.getElementById("templateModalBody");
        if (modalBody) {
          modalBody.innerHTML = `
            <h5><strong>${escapeHtml(job.title)}</strong></h5>
            <p class="text-muted small"><strong>Área:</strong> ${escapeHtml(job.area)} | <strong>Modalidad:</strong> ${escapeHtml(job.modality)} | <strong>Ubicación:</strong> ${escapeHtml(job.location || "N/A")}</p>
            <hr>
            <h6><strong>Descripción:</strong></h6>
            <p style="white-space: pre-line;" class="small">${escapeHtml(job.description)}</p>
            <h6><strong>Beneficios:</strong></h6>
            <p class="small">${escapeHtml(job.benefits || "Ninguno especificado")}</p>
            <h6><strong>Habilidades técnicas:</strong></h6>
            <p class="small">${(job.technical_skills || []).join(", ") || "Ninguna"}</p>
            <h6><strong>Habilidades blandas:</strong></h6>
            <p class="small">${(job.soft_skills || []).join(", ") || "Ninguna"}</p>
          `;
        }

        const modalEl = document.getElementById("templateDetailModal");
        if (modalEl) new bootstrap.Modal(modalEl).show();
      });
    });

    document.querySelectorAll(".select-template-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const jobId = e.currentTarget.dataset.id;
        fillFormWithTemplate(jobId);
      });
    });
  }

  document
    .getElementById("confirmSelectTemplateModalBtn")
    ?.addEventListener("click", () => {
      if (selectedTemplateIdForModal) {
        fillFormWithTemplate(selectedTemplateIdForModal);
        const modalEl = document.getElementById("templateDetailModal");
        const modalInstance = bootstrap.Modal.getInstance(modalEl);
        if (modalInstance) modalInstance.hide();
      }
    });

  function fillFormWithTemplate(jobId) {
    const job = currentStoredJobs.find((j) => String(j.id) === String(jobId));
    if (!job) {
      alert("No se encontró la información de la plantilla.");
      return;
    }

    fields.title.value = job.title || "";
    fields.area.value = job.area || "";
    fields.profileType.value = job.profile_type || "";
    fields.modality.value = job.modality || "";
    fields.location.value = job.location || "";
    fields.description.value = job.description || "";
    fields.benefits.value = job.benefits || "";
    fields.technicalSkills.value = (job.technical_skills || []).join(", ");
    fields.softSkills.value = (job.soft_skills || []).join(", ");
    fields.deadline.value = "";

    if (templatesSection) templatesSection.classList.add("d-none");
    if (formAndAiWorkspace) formAndAiWorkspace.classList.remove("d-none");
    if (formHeaderTitle) {
      formHeaderTitle.innerHTML = `<i class="bi bi-collection-fill me-2"></i>Nueva Vacante (Basada en plantilla: ${escapeHtml(job.title)})`;
    }
  }

  const showAiNotice = (message, type) => {
    if (!aiNotice) return;
    aiNotice.className = `alert alert-${type} mt-3 mb-0`;
    aiNotice.textContent = message;
  };

  const fillFromDraft = (draft) => {
    const textFields = [
      ["title", fields.title],
      ["area", fields.area],
      ["profile_type", fields.profileType],
      ["location", fields.location],
      ["description", fields.description],
      ["benefits", fields.benefits],
    ];
    textFields.forEach(([key, field]) => {
      if (typeof draft[key] === "string" && draft[key].trim()) {
        field.value = draft[key].trim();
      }
    });

    if (
      Array.isArray(draft.technical_skills) &&
      draft.technical_skills.length
    ) {
      fields.technicalSkills.value = draft.technical_skills.join(", ");
    }
    if (Array.isArray(draft.soft_skills) && draft.soft_skills.length) {
      fields.softSkills.value = draft.soft_skills.join(", ");
    }

    const modality = String(draft.modality || "")
      .trim()
      .toLowerCase();
    if (["presencial", "remoto", "hibrido"].includes(modality)) {
      fields.modality.value = modality;
    }
  };

  if (generateDraftButton && aiInstruction) {
    generateDraftButton.addEventListener("click", async () => {
      const instruction = aiInstruction.value.trim();
      if (instruction.length < 3) {
        showAiNotice(
          "Escribe una instrucción o pega el texto de la vacante para generar el borrador.",
          "warning",
        );
        aiInstruction.focus();
        return;
      }

      generateDraftButton.disabled = true;
      generateDraftButton.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2"></span>Generando...';
      if (aiNotice) aiNotice.classList.add("d-none");

      try {
        const response = await fetch(`${API_BASE_URL}/jobs/draft`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ instruction }),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok)
          throw new Error(result.detail || "Error al generar borrador.");

        if (!result.ai_available || !result.draft) {
          showAiNotice("La IA no está disponible en este momento.", "warning");
          return;
        }

        fillFromDraft(result.draft);
        showAiNotice(
          "Borrador generado con éxito. Revisa y completa los datos antes de publicar.",
          "success",
        );
      } catch (error) {
        showAiNotice("No se pudo conectar con el servicio de IA.", "warning");
      } finally {
        generateDraftButton.disabled = false;
        generateDraftButton.innerHTML =
          '<i class="bi bi-magic me-2"></i>Generar borrador';
      }
    });
  }

  // Soporte para modo reapertura
  if (modeParam && modeParam.startsWith("reopen-") && jobIdParam) {
    try {
      const response = await fetch(`${API_BASE_URL}/jobs/${jobIdParam}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const job = await response.json();
      if (!response.ok) throw new Error("No se pudo cargar la vacante.");

      fields.title.value = job.title || "";
      fields.area.value = job.area || "";
      fields.profileType.value = job.profile_type || "";
      fields.modality.value = job.modality || "";
      fields.location.value = job.location || "";
      fields.description.value = job.description || "";
      fields.benefits.value = job.benefits || "";
      fields.technicalSkills.value = (job.technical_skills || []).join(", ");
      fields.softSkills.value = (job.soft_skills || []).join(", ");

      switchViewMode("manual");
      if (formHeaderTitle) formHeaderTitle.textContent = "Reabrir vacante";
      if (submitButton) {
        submitButton.innerHTML =
          '<i class="bi bi-calendar-plus me-2"></i>Guardar y reabrir';
      }
    } catch (error) {
      alert(error.message);
      window.location.href = "jobs.html";
    }
  }
  // Envío del Formulario
  jobForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const deadlineValue = fields.deadline.value;
    let deadline = null;

    if (deadlineValue) {
      const parsedDate = new Date(deadlineValue);
      if (!isNaN(parsedDate.getTime())) {
        if (parsedDate <= new Date()) {
          alert("La fecha límite debe ser posterior al momento actual.");
          return;
        }
        deadline = parsedDate.toISOString();
      }
    }

    const skills = (field) =>
      field.value
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

    const payload = {
      title: fields.title.value.trim(),
      area: fields.area.value.trim(),
      profile_type: fields.profileType.value.trim(),
      modality: fields.modality.value,
      location: fields.location.value.trim() || null,
      description: fields.description.value.trim(),
      technical_skills: skills(fields.technicalSkills),
      soft_skills: skills(fields.softSkills),
      deadline: deadline,
      benefits: fields.benefits.value.trim() || null,
    };

    // Verificamos si realmente es una reapertura clásica o creación normal/plantilla
    const isReopen = modeParam && modeParam.startsWith("reopen-");
    const url = isReopen
      ? `${API_BASE_URL}/jobs/${jobIdParam}/reopen`
      : `${API_BASE_URL}/jobs`;
    const method = isReopen ? "PATCH" : "POST";

    if (submitButton) submitButton.disabled = true;
    try {
      const response = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        // Imprimimos el detalle exacto que manda FastAPI en la consola para depurar fácil
        console.error("Detalle del error 422 de FastAPI:", data);
        throw new Error(
          data.detail
            ? JSON.stringify(data.detail)
            : "No se pudo guardar la vacante.",
        );
      }

      alert(
        isReopen
          ? "Vacante reabierta correctamente."
          : "¡Vacante creada con éxito!",
      );
      window.location.href = "jobs.html";
    } catch (error) {
      alert("Error al guardar.");
    } finally {
      if (submitButton) submitButton.disabled = false;
    }
  });
});
