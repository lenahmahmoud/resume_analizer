import { api, clear, el, toast } from "./api.js";
import { state } from "./state.js";

const fmt = (item, keys) =>
  typeof item === "string" ? item : keys.map((k) => item?.[k]).filter(Boolean).join(" — ");

function listSection(title, items, keys = []) {
  const lines = (items || []).map((item) => fmt(item, keys));
  return el("div", {},
    el("h3", {}, title),
    lines.length ? el("ul", {}, lines.map((line) => el("li", {}, line))) : el("p", { class: "muted" }, "Nothing to show."),
  );
}

function drawReport(box, report) {
  clear(box);
  box.append(
    el("h3", {}, `Target role: ${report.target_role || "-"}`),
    listSection("Missing skills", report.missing_skills, ["skill", "why"]),
    listSection("Weaknesses", report.weaknesses),
    listSection("Suggested improvements", report.improvements),
    listSection("Recommended certifications", report.certifications, ["name", "why"]),
    listSection("Learning resources", report.learning_resources, ["title", "type", "skill"]),
  );
}

function improveSection() {
  const section = el("section", { class: "card" }, el("h2", {}, "Resume improvement"));
  if (!state.resumeId) {
    section.append(el("p", { class: "muted" }, "Upload and select a resume first (My Resumes tab)."));
    return section;
  }

  const jobSelect = el("select", {}, el("option", { value: "" }, "Choose the best role for me"));
  const roleInput = el("input", { type: "text", placeholder: "...or type a target role, e.g. Backend Developer" });
  const button = el("button", { class: "btn primary", onClick: generate }, "Generate report");
  const result = el("div", {});
  section.append(el("div", { class: "row wrap" }, jobSelect, roleInput, button), result);

  (async () => {
    try {
      const jobs = await api("/jobs");
      jobs.forEach((job) => jobSelect.append(el("option", { value: job.id }, `${job.title} — ${job.company}`)));
      if (state.targetJobId) {
        jobSelect.value = String(state.targetJobId);
        state.targetJobId = null;
      }
      const saved = await api(`/advisor/improve/${state.resumeId}`);
      if (saved) drawReport(result, saved);
    } catch (error) {
      toast(error.message, "error");
    }
  })();

  async function generate() {
    button.disabled = true;
    button.textContent = "Generating... please wait";
    try {
      const report = await api(`/advisor/improve/${state.resumeId}`, {
        method: "POST",
        body: {
          target_job_id: jobSelect.value ? Number(jobSelect.value) : null,
          target_role: roleInput.value.trim() || null,
        },
      });
      drawReport(result, report);
    } catch (error) {
      toast(error.message, "error");
    } finally {
      button.disabled = false;
      button.textContent = "Generate report";
    }
  }
  return section;
}

function chatSection() {
  const log = el("div", { class: "chat-log" });
  const input = el("input", { type: "text", placeholder: "Ask e.g. How do I become a backend developer?" });
  const send = el("button", { class: "btn primary", onClick: ask }, "Ask");
  input.addEventListener("keydown", (event) => { if (event.key === "Enter") ask(); });

  function add(who, text) {
    log.append(el("div", { class: `msg ${who}` }, text));
    log.scrollTop = log.scrollHeight;
  }
  add("bot", "Hi! Ask me about skills, courses, certifications or your career path.");

  async function ask() {
    const question = input.value.trim();
    if (question.length < 3) return toast("Type a longer question", "error");
    add("user", question);
    input.value = "";
    send.disabled = true;
    try {
      const reply = await api("/advisor/chat", { method: "POST", body: { question, resume_id: state.resumeId } });
      add("bot", reply.answer);
    } catch (error) {
      add("bot", `Error: ${error.message}`);
    } finally {
      send.disabled = false;
    }
  }

  return el("section", { class: "card" }, el("h2", {}, "Career Advisor chat"), log, el("div", { class: "row" }, input, send));
}

export function renderAdvisor(root) {
  root.append(improveSection(), chatSection());
}