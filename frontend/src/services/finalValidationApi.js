export async function submitFinalValidation({ apiBaseUrl, token, tenantId, payload }) {
  const response = await fetch(`${apiBaseUrl}/api/v1/dashboard/final-validation/master-pdf`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      "x-tenant-id": tenantId,
    },
    body: JSON.stringify(payload),
  });

  const text = await response.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = { raw: text };
  }

  if (!response.ok) {
    const message = body?.detail || body?.message || `${response.status} ${response.statusText}`;
    throw new Error(message);
  }

  return body;
}