import { API_BASE_URL } from "../config.js";

document.addEventListener("DOMContentLoaded", async () => {
  const jobForm = document.getElementById("publishJobForm");
  if (!jobForm) return;

  const params = new URLSearchParams(window.location.search);
  const mode = params.get("mode");
  const jobId = params.get("id");
  const reopenType =
    mode === "reopen-closed"
      ? "closed"
      : mode === "reopen-expired"
        ? "expired"
        : null;
  const token = localStorage.getItem("access_token");

  if (!token) {
    alert("Debes iniciar sesión para publicar o reabrir una vacante.");
    window.location.href = "/login.html";
    return;
  }

  if (mode && (!reopenType || !jobId)) {
    alert("El enlace para reabrir la vacante no es válido.");
    window.location.href = "jobs.html";
    return;
  }

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
  const submitButton = jobForm.querySelector('button[type="submit"]');
  const resetButton = jobForm.querySelector('button[type="reset"]');
  const aiDraftSection = document.querySelector("#aiJobInstruction")?.closest("section");
  const aiInstruction = document.getElementById("aiJobInstruction");
  const generateDraftButton = document.getElementById("generateJobDraftButton");
  const aiNotice = document.getElementById("jobAiNotice");

  if (reopenType && aiDraftSection) aiDraftSection.classList.add("d-none");

  const showAiNotice = (message, type) => {
    if (!aiNotice) return;
    aiNotice.className = `alert alert-${type} mt-3 mb-0`;
    aiNotice.textContent = message;
    aiNotice.setAttribute(
      "role",
      type === "warning" || type === "danger" ? "alert" : "status",
    );
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

    if (Array.isArray(draft.technical_skills) && draft.technical_skills.length) {
      fields.technicalSkills.value = draft.technical_skills.join(", ");
    }
    if (Array.isArray(draft.soft_skills) && draft.soft_skills.length) {
      fields.softSkills.value = draft.soft_skills.join(", ");
    }

    const modality = String(draft.modality || "")
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
    if (["presencial", "remoto", "hibrido"].includes(modality)) {
      fields.modality.value = modality;
    }

    if (typeof draft.deadline === "string" && draft.deadline.trim()) {
      const deadlineDate = new Date(draft.deadline);
      if (!Number.isNaN(deadlineDate.getTime())) {
        fields.deadline.value = toLocalDateTimeInputValue(deadlineDate);
      }
    }
  };

  // Si se cargan los botones para generar la vacante con IA y el campo de texto para escribir la instrucción
  if (generateDraftButton && aiInstruction) {
    generateDraftButton.addEventListener("click", async () => {
      const instruction = aiInstruction.value.trim();
      if (instruction.length < 3) {
        showAiNotice("Escribe una instrucción o pega el texto de la vacante para generar el borrador.", "warning");
        aiInstruction.focus();
        return;
      }

      generateDraftButton.disabled = true;
      generateDraftButton.setAttribute("aria-busy", "true");
      generateDraftButton.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Generando...';
      if (aiNotice) aiNotice.classList.add("d-none");

      // Intenta llamar a la IA para generar el borrador
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
        if (!response.ok) {
          const detail =
            typeof result.detail === "string"
              ? result.detail
              : "No se pudo contactar el servicio de generación de vacantes.";
          throw new Error(detail);
        }

        // Si no está disponible la IA o no se devuelve un borrador
        if (!result.ai_available || !result.draft) {
          showAiNotice(
            "La IA no está disponible en este momento. Inténtalo más tarde o completa el formulario manualmente.",
            "warning",
          );
          return;
        }

        fillFromDraft(result.draft);
        showAiNotice(
          "Borrador generado. Revisa la información y completa cualquier campo faltante antes de publicar.",
          "success",
        );
      } catch (error) {    
        showAiNotice(
          "La IA no está disponible en este momento. Inténtalo más tarde o completa el formulario manualmente.",
          "warning",
        );
      } finally {
        generateDraftButton.disabled = false;
        generateDraftButton.removeAttribute("aria-busy");
        generateDraftButton.innerHTML =
          '<i class="bi bi-magic me-2" aria-hidden="true"></i>Generar borrador';
      }
    });
  }

  // Si se pulsa el botón para reabrir una vacante
  if (reopenType) {
    const header = document.querySelector(".card-header .card-title");
    const notice = document.createElement("div");
    notice.className = "alert alert-info";
    notice.setAttribute("role", "status");
    jobForm.before(notice);

    try {
      const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const job = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error("No se pudo cargar la vacante.");
      }
      if (job.status !== reopenType) {
        throw new Error(
          "El estado de la vacante cambió. Regresa a la lista y vuelve a intentarlo.",
        );
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
      if (job.deadline) {
        const localDeadline = new Date(job.deadline);
        localDeadline.setMinutes(
          localDeadline.getMinutes() - localDeadline.getTimezoneOffset(),
        );
        fields.deadline.value = localDeadline.toISOString().slice(0, 16);
      }

      if (reopenType === "closed") {
        if (header) header.textContent = "Editar y reabrir vacante";
        notice.textContent =
          "Revisa los datos de la vacante cerrada. Al guardar, se actualizará esta misma vacante y volverá a aceptar postulaciones.";
        if (submitButton) {
          submitButton.innerHTML =
            '<i class="bi bi-arrow-counterclockwise me-2"></i>Guardar cambios y reabrir';
        }
      } else {
        if (header) header.textContent = "Extender fecha y reabrir vacante";
        notice.textContent =
          "Esta vacante venció. Sus datos no se pueden editar aquí; indica una nueva fecha límite futura para reabrirla.";
        Object.entries(fields).forEach(([name, field]) => {
          if (name !== "deadline") field.disabled = true;
        });
        fields.deadline.required = true;
        fields.deadline.min = toLocalDateTimeInputValue(new Date());
        if (resetButton) resetButton.classList.add("d-none");
        if (submitButton) {
          submitButton.innerHTML =
            '<i class="bi bi-calendar-plus me-2"></i>Guardar fecha y reabrir';
        }
      }
    } catch (error) {
      alert(error.message);
      window.location.href = "jobs.html";
      return;
    }
  }

  jobForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const deadlineValue = fields.deadline.value;
    const deadline = deadlineValue
      ? new Date(deadlineValue).toISOString()
      : null;

    // Si la vacante a reabrir era vencida tiene que tener una fecha límite futura. Los demás datos no cambiarán.
    if (reopenType === "expired") {
      if (!deadlineValue || new Date(deadlineValue) <= new Date()) {
        alert("Selecciona una nueva fecha límite futura.");
        return;
      }
    }

    const skills = (field) =>
      field.value
        .split(",")
        .map((skill) => skill.trim())
        .filter(Boolean);

    const payload =
      reopenType === "expired"
        ? { deadline }
        : {
            title: fields.title.value.trim(),
            area: fields.area.value.trim(),
            profile_type: fields.profileType.value.trim(),
            modality: fields.modality.value,
            location: fields.location.value.trim() || null,
            description: fields.description.value.trim(),
            technical_skills: skills(fields.technicalSkills),
            soft_skills: skills(fields.softSkills),
            deadline,
            benefits: fields.benefits.value.trim() || null,
          };

    const url = reopenType
      ? `${API_BASE_URL}/jobs/${jobId}/reopen`
      : `${API_BASE_URL}/jobs`;
    const method = reopenType ? "PATCH" : "POST";

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
        const detail =
          typeof data.detail === "string"
            ? data.detail
            : "Revisa los campos ingresados e inténtalo nuevamente.";
        throw new Error(detail);
      }

      const successMessage = reopenType
        ? "La vacante existente se reabrió correctamente."
        : "¡Vacante creada con éxito!";
      alert(successMessage);
      window.location.href = "jobs.html";
    } catch (error) {
      alert(error.message || "No se pudo guardar la vacante.");
    } finally {
      if (submitButton) submitButton.disabled = false;
    }
  });
});

function toLocalDateTimeInputValue(date) {
  const localDate = new Date(date);
  localDate.setMinutes(localDate.getMinutes() - localDate.getTimezoneOffset());
  return localDate.toISOString().slice(0, 16);
}
