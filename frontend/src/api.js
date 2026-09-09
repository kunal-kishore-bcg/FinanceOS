const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function extractErrorDetail(response, fallback) {
  try {
    const data = await response.json();
    return data.detail || fallback;
  } catch {
    return fallback;
  }
}

async function request(path, { method = "GET", body, token } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    throw new Error(await extractErrorDetail(response, `Request failed (${response.status})`));
  }
  if (response.status === 204) return null;
  return response.json();
}

export async function login(email, password) {
  // /auth/login is FastAPI's OAuth2PasswordRequestForm — it expects
  // application/x-www-form-urlencoded with username/password fields,
  // NOT JSON. Kept as-is on the backend since that's what makes the
  // Swagger "Authorize" button work there too, so the frontend has to
  // speak that format rather than the JSON the rest of the API uses.
  const formBody = new URLSearchParams();
  formBody.set("username", email);
  formBody.set("password", password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formBody,
  });

  if (!response.ok) {
    throw new Error(await extractErrorDetail(response, "Incorrect email or password"));
  }
  return response.json(); // { access_token, token_type, role }
}

export function fetchInvoices(token) {
  return request("/invoices/", { token });
}

export function createInvoice(token, invoice) {
  return request("/invoices/", { method: "POST", token, body: invoice });
}

export function decideInvoice(token, invoiceId, decision, reason) {
  return request(`/invoices/${invoiceId}/decision`, {
    method: "PATCH",
    token,
    body: { decision, reason },
  });
}

export async function uploadInvoicePdf(token, file) {
  // Deliberately not using request() — that helper always sets
  // Content-Type: application/json. A multipart upload needs the
  // browser to set Content-Type itself (with the correct boundary
  // string), so this builds its own fetch call instead of forcing
  // FormData through a JSON-shaped wrapper.
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/invoices/upload-pdf`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await extractErrorDetail(response, "Could not process this PDF"));
  }
  return response.json();
}
