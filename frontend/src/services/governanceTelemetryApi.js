export async function fetchClosedLoopTelemetry(apiBaseUrl) {
  const response = await fetch(`${apiBaseUrl}/api/v1/public/closed-loop/telemetry`);
  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(body?.detail || `${response.status} ${response.statusText}`);
  }

  return body;
}
