import { API_BASE_URL } from "../config.js";

document.addEventListener("DOMContentLoaded", () => {
  const jobForm = document.getElementById("publishJobForm");

  if (!jobForm) return;

  jobForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const token = localStorage.getItem("access_token");
    if (!token) {
      alert("Debes iniciar sesión para publicar una vacante.");
      window.location.href = "/login.html";
      return;
    }

    // Captura segura de valores
    const deadlineVal = document.getElementById("jobDeadline").value;
    const optionalVal = document.getElementById("optionalSkills").value;

    const payload = {
      title: document.getElementById("jobTitle").value,
      area: document.getElementById("jobArea").value,
      profile_type: document.getElementById("profileType").value,
      modality: document.getElementById("jobModality").value,
      location: document.getElementById("jobLocation").value || null,
      description: document.getElementById("jobDescription").value,
      required_skills: document
        .getElementById("requiredSkills")
        .value.split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      // Si está vacío, debe ser un arreglo vacío []
      optional_skills: optionalVal
        ? optionalVal
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean)
        : [],
      // Si está vacío, debe ser null (no una cadena de texto vacía "")
      deadline: deadlineVal ? new Date(deadlineVal).toISOString() : null,
      status: "active",
    };

    try {
      // Nótese la barra diagonal final al final de /jobs/
      const response = await fetch(`${API_BASE_URL}/jobs/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (response.ok) {
        alert("¡Vacante creada con éxito!");
        window.location.href = "/src/pages/recruiter/jobs.html";
      } else {
        // En caso de error 422, data.detail contiene exactamente qué campo falló
        console.error("Detalle del error de validación:", data.detail);
        alert(`Error en la validación de datos (422). Revisa la consola.`);
      }
    } catch (error) {
      console.error("Error al conectar con la API:", error);
    }
  });
});
