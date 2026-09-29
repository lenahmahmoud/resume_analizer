import { api, chips, clear, el, toast } from "./api.js";
import { state } from "./state.js";

export function renderResumes(root) {
  const fileInput = el("input", { type: "file", accept: ".pdf,.docx" });
  const uploadBtn = el("button", { class: "btn primary", onClick: upload }, "Upload & Analyze");
  const listBox = el("section", { class: "card" });
  const detailBox = el("div", {});

  root.append(
    el("section", { class: "card" },
      el("h2", {}, "Upload your resume"),
      el("p", { class: "muted" }, "PDF or DOCX, maximum 5 MB."),
      el("div", { class: "row" }, fileInput, uploadBtn),
    ),
    listBox,
    detailBox,
  );
  loadList().catch((error) => toast(error.message, "error"));

  async function upload() {
    const file = fileInput.files[0];
    if (!file) return toast("Choose a file first", "error");
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["pdf", "docx"].includes(ext)) return toast("Only PDF and DOCX files are allowed", "error");
    if (file.size > 5 * 1024 * 1024) return toast("The file is larger than 5 MB", "error");

    uploadBtn.disabled = true;
    uploadBtn.textContent = "Analyzing... please wait";
    try {
      const form = new FormData();
      form.append("file", file);
      const resume = await api("/resumes", { method: "POST", formData: form });
      state.resumeId = resume.id;
      fileInput.value = "";
      await api(`/resumes/${resume.id}/analyze`, { method: "POST" });
      toast("Resume analyzed!", "success");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      uploadBtn.disabled = false;
      uploadBtn.textContent = "Upload & Analyze";
      loadList().catch((error) => toast(error.message, "error"));
    }
  }

  async function loadList() {
    const resumes = await api("/resumes");
    clear(listBox);
    clear(detailBox);
    listBox.append(el("h2", {}, "My resumes"));
    if (!resumes.length) {
      state.resumeId = null;
      listBox.append(el("p", { class: "muted" }, "No resumes yet. Upload one above."));
      return;
    }
    if (!resumes.some((r) => r.id === state.resumeId)) state.resumeId = resumes[0].id;

    resumes.forEach((r) => {
      listBox.append(
        el("div", { class: `list-item ${r.id === state.resumeId ? "selected" : ""}` },
          el("div", {},
            el("strong", {}, r.filename),
            el("div", { class: "muted" }, `${new Date(r.uploaded_at + "Z").toLocaleString()} · ${r.analyzed ? "analyzed" : "not analyzed"}`),
          ),
          el("div", { class: "row" },
            el("button", { class: "btn", onClick: () => { state.resumeId = r.id; loadList(); } }, "View"),
            el("button", { class: "btn danger", onClick: () => remove(r.id) }, "Delete"),
          ),
        ),
      );
    });
    await showDetail(state.resumeId);
  }

  async function remove(id) {
    if (!confirm("Delete this resume and everything linked to it?")) return;
    try {
      await api(`/resumes/${id}`, { method: "DELETE" });
      if (state.resumeId === id) state.resumeId = null;
      toast("Resume deleted", "success");
      await loadList();
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function showDetail(id) {
    const resume = await api(`/resumes/${id}`);
    clear(detailBox);

    if (!resume.analysis) {
      const button = el("button", { class: "btn primary" }, "Analyze now");
      button.addEventListener("click", async () => {
        button.disabled = true;
        button.textContent = "Analyzing...";
        try {
          await api(`/resumes/${id}/analyze`, { method: "POST" });
          await loadList();
        } catch (error) {
          toast(error.message, "error");
          button.disabled = false;
          button.textContent = "Analyze now";
        }
      });
      detailBox.append(el("section", { class: "card" }, el("p", {}, "This resume has not been analyzed yet."), button));
      return;
    }

    const a = resume.analysis;
    const contact = [a.contact?.name, a.contact?.email, a.contact?.phone].filter(Boolean).join(" · ");
    detailBox.append(
      el("section", { class: "card" },
        el("h2", {}, "Analysis"),
        contact ? el("p", { class: "muted" }, contact) : null,
        el("h3", {}, "Summary"),
        el("p", {}, a.summary || "-"),
        el("p", { class: "muted" }, `Years of experience: ${a.years_of_experience}`),
        el("h3", {}, "Technical skills"), chips(a.technical_skills),
        el("h3", {}, "Soft skills"), chips(a.soft_skills),
        el("h3", {}, "Education"),
        a.education.length
          ? el("ul", {}, a.education.map((e) => el("li", {}, [e.degree, e.institution, e.year].filter(Boolean).join(" — "))))
          : el("p", { class: "muted" }, "None found"),
        el("h3", {}, "Experience"),
        a.experience.length
          ? a.experience.map((e) =>
              el("div", {},
                el("strong", {}, `${e.title || ""} ${e.company ? "at " + e.company : ""}`),
                el("span", { class: "muted" }, e.duration ? ` (${e.duration})` : ""),
                el("ul", {}, (e.highlights || []).map((h) => el("li", {}, h))),
              ))
          : el("p", { class: "muted" }, "None found"),
        el("div", { class: "row" },
          el("button", { class: "btn primary", onClick: () => window.dispatchEvent(new CustomEvent("navigate", { detail: "matching" })) }, "Find matching jobs →"),
          el("button", { class: "btn", onClick: () => window.dispatchEvent(new CustomEvent("navigate", { detail: "advisor" })) }, "Improve my resume →"),
        ),
      ),
    );
  }
}