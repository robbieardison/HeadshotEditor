const DEFAULT_API = "http://localhost:8000";

function apiBase(): string {
  const url = import.meta.env.VITE_API_URL;
  return typeof url === "string" && url.length > 0 ? url.replace(/\/$/, "") : DEFAULT_API;
}

export async function removeBackground(file: File): Promise<Blob> {
  const body = new FormData();
  body.append("file", file);

  const res = await fetch(`${apiBase()}/api/remove-background`, {
    method: "POST",
    body,
  });

  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const j = JSON.parse(text) as {
        detail?: unknown;
      };
      if (typeof j.detail === "string") {
        detail = j.detail;
      } else if (Array.isArray(j.detail) && j.detail[0]) {
        const first = j.detail[0] as { msg?: string };
        if (typeof first.msg === "string") detail = first.msg;
      }
    } catch {
      /* use raw */
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }

  return res.blob();
}
