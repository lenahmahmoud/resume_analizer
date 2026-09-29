import { api, chips, clear, el, toast } from "./api.js";

const JOB_TYPES = ["Full-time", "Part-time", "Internship", "Contract"];
const labeled = (text, input) => el("label", { class: "field" }, text, input);

export function renderJobs(root) {
  const filters = {
    q: el("input", { type: "text", placeholder: "Keyword (title, company, description)" }),
    location: el("input", { type: "text", placeholder: "Location" }),
    skill: el("input", { type: "text", placeholder: "Skill" }),
    job_type: el("select", {}, [el("option", { value: "" }, "Any type"), ...JOB_TYPES.map((t) => el("option", { value: t }, t))]),
  };
  const formBox = el("div", {});
  const listBox = el("div", {});

  root.append(
    el("section", { class: "card" },
      el("h2", {}, "Search jobs"),
      el("div", { class: "row wrap" },
        Object.values(filters),
        el("button", { class: "btn primary", onClick: load }, "Search"),
        el("button", { class: "btn", onClick: resetFilters }, "Reset"),
        el("button", { class: "btn success", onClick: () => showForm() }, "+ Add job"),
      ),
    ),
    formBox,
    listBox,
  );
  load();

  function resetFilters() {
    Object.values(filters).forEach((input) => (input.value = ""));
    load();
  }

  async function load() {
    const params = new URLSearchParams();
    for (const [key, input] of Object.entries(filters)) {
      if (input.value.trim()) params.set(key, input.value.trim());
    }
    try {
      const jobs = await api(`/jobs?${params}`);
      clear(listBox);
      if (!jobs.length) {
        listBox.append(el("p", { class: "muted" }, "No jobs found."));
        return;
      }
      jobs.forEach((job) => listBox.append(jobCard(job)));
    } catch (error) {
      toast(error.message, "error");
    }
  }

  function jobCard(job) {
    return el("article", { class: "card" },
      el("div", { class: "row space" },
        el("h3", {}, `${job.title} — ${job.company}`),
        el("div", { class: "row" },
          el("button", { class: "btn", onClick: () => showForm(job) }, "Edit"),
          el("button", { class: "btn danger", onClick: () => remove(job) }, "Delete"),
        ),
      ),
      el("p", { class: "muted" }, `${job.location} · ${job.job_type}`),
      el("p", {}, job.description),
      chips(job.required_skills),
    );
  }

  async function remove(job) {
    if (!confirm(`Delete "${job.title}"?`)) return;
    try {
      await api(`/jobs/${job.id}`, { method: "DELETE" });
      toast("Job deleted", "success");
      load();
    } catch (error) {
      toast(error.message, "error");
    }
  }

  function showForm(job = null) {
    clear(formBox);
    const fields = {
      title: el("input", { type: "text", value: job ? job.title : "", placeholder: "Job title" }),
      company: el("input", { type: "text", value: job ? job.company : "", placeholder: "Company" }),
      location: el("input", { type: "text", value: job ? job.location : "", placeholder: "City or Remote" }),
      job_type: el("select", {}, JOB_TYPES.map((t) => el("option", { value: t }, t))),
      required_skills: el("input", { type: "text", value: job ? job.required_skills.join(", ") : "", placeholder: "Python, FastAPI, SQL" }),
      description: el("textarea", { rows: 5, placeholder: "At least 20 characters" }, job ? job.description : ""),
    };
    if (job) fields.job_type.value = job.job_type;

    async function save() {
      const body = {
        title: fields.title.value.trim(),
        company: fields.company.value.trim(),
        location: fields.location.value.trim() || "Remote",
        job_type: fields.job_type.value,
        description: fields.description.value.trim(),
        required_skills: fields.required_skills.value.split(",").map((s) => s.trim()).filter(Boolean),
      };
      if (body.title.length < 2 || !body.company || body.description.length < 20) {
        return toast("Title, company and a description (20+ characters) are required", "error");
      }
      try {
        await api(job ? `/jobs/${job.id}` : "/jobs", { method: job ? "PUT" : "POST", body });
        toast("Job saved", "success");
        clear(formBox);
        load();
      } catch (error) {
        toast(error.message, "error");
      }
    }

    formBox.append(
      el("section", { class: "card" },
        el("h2", {}, job ? "Edit job" : "Add job"),
        labeled("Title", fields.title),
        labeled("Company", fields.company),
        labeled("Location", fields.location),
        labeled("Job type", fields.job_type),
        labeled("Required skills (comma separated)", fields.required_skills),
        labeled("Description", fields.description),
        el("div", { class: "row" },
          el("button", { class: "btn primary", onClick: save }, "Save"),
          el("button", { class: "btn", onClick: () => clear(formBox) }, "Cancel"),
        ),
      ),
    );
    formBox.scrollIntoView({ behavior: "smooth" });
  }
}