import { api, chips, clear, el, toast } from "./api.js";
import { state } from "./state.js";

export function renderMatching(root) {
  if (!state.resumeId) {
    root.append(el("div", { class: "card" }, el("p", {}, "Upload and select a resume first (My Resumes tab).")));
    return;
  }

  const button = el("button", { class: "btn primary", onClick: run }, "Find matching jobs");
  const results = el("div", {});
  root.append(
    el("section", { class: "card" },
      el("h2", {}, "Job recommendations"),
      el("p", { class: "muted" }, "Your resume is compared with every job. Score = 60% skill overlap + 40% AI similarity."),
      button,
    ),
    results,
  );
  load();

  async function load() {
    try { draw(await api(`/matching/${state.resumeId}`)); } catch (error) { toast(error.message, "error"); }
  }

  async function run() {
    button.disabled = true;
    button.textContent = "Matching... please wait";
    try {
      draw(await api(`/matching/${state.resumeId}`, { method: "POST" }));
    } catch (error) {
      toast(error.message, "error");
    } finally {
      button.disabled = false;
      button.textContent = "Find matching jobs";
    }
  }

  function draw(matches) {
    clear(results);
    if (!matches.length) {
      results.append(el("p", { class: "muted" }, "No results yet. Click the button above."));
      return;
    }
    matches.forEach((m) => {
      results.append(
        el("article", { class: "card" },
          el("div", { class: "row space" },
            el("h3", {}, `${m.title} — ${m.company}`),
            el("span", { class: "score" }, `${m.score}%`),
          ),
          el("div", { class: "bar" }, el("div", { class: "bar-fill", style: `width:${Number(m.score)}%` })),
          el("p", { class: "muted" }, `${m.location} · ${m.job_type}`),
          el("p", {}, m.explanation || "No explanation available."),
          el("strong", {}, "Matched skills"), chips(m.matched_skills, "ok"),
          el("strong", {}, "Missing skills"), chips(m.missing_skills, "bad"),
          el("button", {
            class: "btn",
            onClick: () => {
              state.targetJobId = m.job_id;
              window.dispatchEvent(new CustomEvent("navigate", { detail: "advisor" }));
            },
          }, "Improve my resume for this job"),
        ),
      );
    });
  }
}