// Manejo de Tokens JWT (LocalStorage/SessionStorage), Login Google
import { API_BASE_URL } from "./config.js";

document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("loginForm");

  if (!loginForm) return;

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (response.ok) {
        //  EL PASO CLAVE: Guardar el token devuelto en el localStorage del navegador
        localStorage.setItem("access_token", data.access_token);
        alert("¡Inicio de sesión exitoso!");

        // Redirigir directamente a la pantalla de vacantes
        window.location.href = "../pages/recruiter/jobs.html";
      } else {
        alert(
          `Error al iniciar sesión: ${data.detail || "Credenciales incorrectas"}`,
        );
      }
    } catch (error) {
      console.error("Error en la autenticación:", error);
      alert("No se pudo conectar con el servidor.");
    }
  });
});