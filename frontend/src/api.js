// Deliberately only calls /query and /health — never /ingest. Letting any
// visitor to a public demo trigger re-ingestion (or reset:true) would let
// them wipe the vector store or run up the Groq bill. Ingestion is a step
// you run yourself before deploying, not something the UI exposes.

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

export async function askQuestion(question) {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // response wasn't JSON — keep the generic message
    }
    throw new Error(detail);
  }

  return res.json(); // { answer, sources, accepted, reason }
}
