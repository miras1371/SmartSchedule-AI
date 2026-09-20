const apiBase = "http://localhost:8000";
const form = document.querySelector("#login-form");
const usernameInput = document.querySelector("#username");
const passwordInput = document.querySelector("#password");
const errorBox = document.querySelector("#login-error");

function setError(message) {
  errorBox.textContent = message || "";
}

if (localStorage.getItem("smart_schedule_token")) {
  window.location.href = "home.html";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setError("");

  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  if (!username || !password) {
    setError("Введите логин и пароль.");
    return;
  }

  try {
    const response = await fetch(`${apiBase}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Не удалось войти в систему");
    }

    localStorage.setItem("smart_schedule_token", data.access_token);
    localStorage.setItem("smart_schedule_user", JSON.stringify(data.user));
    window.location.href = "home.html";
  } catch (error) {
    setError(error.message || "Ошибка входа");
  }
});
