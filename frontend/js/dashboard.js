import { api, auth, clear, el } from "./api.js";
import { renderAdvisor } from "./advisor.js";
import { renderJobs } from "./jobs.js";
import { renderMatching } from "./matching.js";
import { renderResumes } from "./resumes.js";

const views = [
  { id: "resumes", label: "My Resumes", render: renderResumes },
  { id: "matching", label: "Job Matches", render: renderMatching },
  { id: "advisor", label: "Career Advisor", render: renderAdvisor },
  { id: "jobs", label: "Jobs", render: renderJobs },
];

function show(id) {
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.id === id));
  const main = document.getElementById("view");
  clear(main);
  views.find((view) => view.id === id).render(main);
}

async function logout() {
  try { await api("/auth/logout", { method: "POST" }); } catch { /* ignore */ }
  auth.clear();
  window.location.href = "/index.html";
}

function start() {
  const user = auth.getUser();
  const nav = el("nav", { class: "tabs" },
    views.map((view) => el("button", { class: "tab", dataset: { id: view.id }, onClick: () => show(view.id) }, view.label)));

  document.getElementById("app").append(
    el("header", { class: "topbar" },
      el("h1", {}, "AI Resume Analyzer"),
      el("div", { class: "user" }, el("span", {}, user ? user.name : ""), el("button", { class: "btn", onClick: logout }, "Logout")),
    ),
    nav,
    el("main", { id: "view", class: "container" }),
  );

  // Other files ask to switch tab with: window.dispatchEvent(new CustomEvent("navigate", { detail: "matching" }))
  window.addEventListener("navigate", (event) => show(event.detail));
  show("resumes");
}

if (!auth.getToken()) window.location.href = "/index.html";
else start();