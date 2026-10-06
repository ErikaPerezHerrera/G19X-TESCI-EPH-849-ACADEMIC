(function checkAuthGuard() {
  const token = localStorage.getItem("access_token");
  const role = localStorage.getItem("user_role");
  const pathname = window.location.pathname || "";

  const isRecruiterPage = pathname.includes("/recruiter/");
  const isCandidatePage = pathname.includes("/candidate/");

  if (!token) {
    window.location.replace("../login.html");
    return;
  }

  const recruiterRoles = ["recruiter", "admin"];
  const candidateRoles = ["casual", "registered"];

  if (isRecruiterPage) {
    if (!role || !recruiterRoles.includes(role)) {
      const fallback = candidateRoles.includes(role) ? "../candidate/dashboard.html" : "../login.html";
      window.location.replace(fallback);
      return;
    }
  }

  if (isCandidatePage) {
    if (!role || !candidateRoles.includes(role)) {
      const fallback = recruiterRoles.includes(role) ? "../recruiter/jobs.html" : "../login.html";
      window.location.replace(fallback);
      return;
    }
  }
})();
