//# Publicación de vacante, lista con orden por match
async function handleCreateJob(event) {
  event.preventDefault();

  const token = localStorage.getItem("access_token");
  if (!token) {
    alert("Debes iniciar sesión como reclutador.");
    window.location.href = "/login.html";
    return;
  }

  const payload = {
    title: document.getElementById("jobTitle").value,
    area: document.getElementById("jobArea").value,
    profile_type: document.getElementById("profileType").value,
    modality: document.getElementById("jobModality").value, // "presencial" | "remoto" | "hibrido"
    location: document.getElementById("jobLocation").value || null,
    description: document.getElementById("jobDescription").value,
    required_skills: document
      .getElementById("requiredSkills")
      .value.split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    optional_skills: document
      .getElementById("optionalSkills")
      .value.split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    deadline: document.getElementById("jobDeadline").value
      ? new Date(document.getElementById("jobDeadline").value).toISOString()
      : null,
  };

  try {
    const response = await fetch("http://localhost:8000/api/v1/jobs/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (response.ok) {
      const data = await response.json();
      alert("¡Vacante creada con éxito!");
      window.location.href = "/dashboard-recruiter.html";
    } else {
      const errorData = await response.json();
      alert(`Error: ${errorData.detail}`);
    }
  } catch (error) {
    console.error("Error al conectar con la API:", error);
  }
}