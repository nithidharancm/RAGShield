const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://ragshield-nw4s.onrender.com";

async function parseResponse(response) {
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail = payload?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item?.msg || "Validation error").join(", ")
      : detail || payload?.message || `Request failed (${response.status})`;

    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

export async function checkHealth() {
  const response = await fetch(`${API_BASE}/health`);
  return parseResponse(response);
}

export async function secureSearch(userId, query, ragshieldEnabled = true) {
  const started = performance.now();

  const response = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      user_id: userId,
      query,
      ragshield_enabled: ragshieldEnabled,
    }),
  });

  const payload = await parseResponse(response);
  const latencyMs = Math.round(performance.now() - started);

  return { payload, latencyMs };
}

export async function uploadAndScan(file, tenantId, ragshieldEnabled = true) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("tenant_id", tenantId);
  formData.append("ragshield_enabled", String(ragshieldEnabled));

  const uploadResponse = await fetch(`${API_BASE}/documents/upload`, {
    method: "POST",
    body: formData,
    headers: { Accept: "application/json" },
  });

  const upload = await parseResponse(uploadResponse);

  const scanResponse = await fetch(
    `${API_BASE}/documents/${encodeURIComponent(upload.document_id)}/scan`,
    {
      method: "POST",
      headers: { Accept: "application/json" },
    }
  );

  const scan = await parseResponse(scanResponse);
  return { upload, scan };
}

export { API_BASE };
