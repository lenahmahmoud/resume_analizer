import { api, auth, clear, el } from "./api.js";

if (auth.getToken()) window.location.href = "/dashboard.html";

const app = document.getElementById("app");
let mode = "login";

const field = (label, id, type, placeholder) =>
  el("label", { class: "field" }, label, el("input", { id, type, placeholder }));

function render() {
  clear(app);
  const isLogin = mode === "login";
  app.append(
    el("div", { class: "card auth-card" },
      el("h1", {}, "AI Resume Analyzer"),
      el("p", { class: "muted" }, isLogin ? "Login to your account" : "Create a new account"),
      el("form", { onSubmit: handleSubmit, novalidate: true },
        isLogin ? null : field("Full name", "name", "text", "Your full name"),
        field("Email", "email", "email", "you@example.com"),
        field("Password", "password", "password", isLogin ? "Your password" : "At least 8 characters"),
        el("p", { class: "error", id: "error" }),
        el("button", { type: "submit", class: "btn primary block", id: "submitBtn" }, isLogin ? "Login" : "Register"),
      ),
      el("p", { class: "muted center" },
        isLogin ? "No account yet? " : "Already registered? ",
        el("a", {
          href: "#",
          onClick: (event) => { event.preventDefault(); mode = isLogin ? "register" : "login"; render(); },
        }, isLogin ? "Register" : "Login"),
      ),
    ),
  );
}

async function handleSubmit(event) {
  event.preventDefault();
  const errorBox = document.getElementById("error");
  const button = document.getElementById("submitBtn");
  errorBox.textContent = "";

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const name = mode === "register" ? document.getElementById("name").value.trim() : "";

  if (mode === "register" && name.length < 2) return (errorBox.textContent = "Please enter your name (2+ characters).");
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return (errorBox.textContent = "Please enter a valid email address.");
  if (!password) return (errorBox.textContent = "Please enter your password.");
  if (mode === "register" && password.length < 8) return (errorBox.textContent = "Password must be at least 8 characters.");

  button.disabled = true;
  try {
    const data = mode === "login"
      ? await api("/auth/login", { method: "POST", body: { email, password } })
      : await api("/auth/register", { method: "POST", body: { name, email, password } });
    auth.setSession(data.access_token, data.user);
    window.location.href = "/dashboard.html";
  } catch (error) {
    errorBox.textContent = error.message;
    button.disabled = false;
  }
}

render();