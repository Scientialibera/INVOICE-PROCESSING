const BASE = "";

async function request(path, options = {}, token) {
  const headers = { ...options.headers };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

export async function fetchDashboard(token) {
  return request("/api/dashboard", {}, token);
}

export async function fetchInvoices(token, offset = 0, limit = 50) {
  return request(`/api/invoices?offset=${offset}&limit=${limit}`, {}, token);
}

export async function fetchInvoice(token, id) {
  return request(`/api/invoices/${id}`, {}, token);
}

export async function updateInvoice(token, id, updates) {
  return request(
    `/api/invoices/${id}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    },
    token
  );
}

export async function deleteInvoice(token, id) {
  return request(`/api/invoices/${id}`, { method: "DELETE" }, token);
}

export async function uploadInvoice(token, file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export function streamChat(token, message, onChunk, onDone, onError) {
  const controller = new AbortController();

  fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const json = line.slice(6).trim();
          if (!json) continue;
          try {
            const parsed = JSON.parse(json);
            if (parsed.type === "done") {
              onDone?.();
            } else if (parsed.type === "error") {
              onError?.(parsed.content);
            } else {
              onChunk(parsed);
            }
          } catch {
            /* skip malformed */
          }
        }
      }
      onDone?.();
    })
    .catch((err) => {
      if (err.name !== "AbortError") onError?.(err.message);
    });

  return () => controller.abort();
}
