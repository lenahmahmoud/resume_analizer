const TOKEN_KEY = "token";
const USER_KEY = "user";

export const auth = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  getUser() {
    try { return JSON.parse(localStorage.getItem(USER_KEY)); } catch { return null; }
  },
  setSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
};

// Calls the backend. Throws an Error with a readable message when something fails.
export async function api(path, { method = "GET", body, formData } = {}) {
  const headers = {};
  const token = auth.getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (formData) {
    payload = formData;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`/api${path}`, { method, headers, body: payload });
  } catch {
    throw new Error("Cannot reach the server. Is it running?");
  }

  const isAuthCall = path.startsWith("/auth/login") || path.startsWith("/auth/register");
  if (response.status === 401 && !isAuthCall) {
    auth.clear();
    window.location.href = "/index.html";
    throw new Error("Session expired. Please log in again.");
  }
  if (response.status === 204) return null;

  let data = null;
  try { data = await response.json(); } catch { /* no JSON body */ }
  if (!response.ok) throw new Error((data && data.detail) || `Request failed (${response.status})`);
  return data;
}

// el("div", { class: "card", onClick: fn }, "text", childNode) -> creates a DOM element
export function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === false || value == null) continue;
    if (key === "class") node.className = value;
    else if (key === "dataset") Object.assign(node.dataset, value);
    else if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2).toLowerCase(), value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child == null || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

export const clear = (node) => node.replaceChildren();

export function chips(list = [], cls = "") {
  if (!list.length) return el("p", { class: "muted" }, "None");
  return el("div", { class: "chips" }, list.map((text) => el("span", { class: `chip ${cls}` }, text)));
}

export function toast(message, type = "info") {
  let box = document.getElementById("toasts");
  if (!box) {
    box = el("div", { id: "toasts" });
    document.body.append(box);
  }
  const item = el("div", { class: `toast ${type}` }, message);
  box.append(item);
  setTimeout(() => item.remove(), 4000);
}