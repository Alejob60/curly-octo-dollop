export async function fetchMasterData(apiBaseUrl) {
  const response = await fetch(`${apiBaseUrl}/api/v1/master-data`);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function suggestDependency(apiBaseUrl, payload) {
  const response = await fetch(`${apiBaseUrl}/api/v1/master-data/suggest-dependency`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const body = await response.json();
  if (!response.ok) {
    throw new Error(body?.detail || `${response.status} ${response.statusText}`);
  }
  return body;
}

export async function submitCitizenPqrs(apiBaseUrl, payload) {
  const formData = new FormData();
  formData.append(
    "citizen_name",
    payload.anonymous_mode ? "ANONIMO PROTEGIDO" : payload.citizen_name || "CIUDADANO PROTEGIDO",
  );
  formData.append("citizen_id", payload.anonymous_mode ? "CC-RESERVADO" : payload.citizen_id || "CC-SIN-DATO");
  formData.append(
    "citizen_email",
    payload.anonymous_mode ? "anonimo@orbital-prime.local" : payload.citizen_email || "sin-correo@cali.gov.co",
  );
  formData.append("content", payload.requested_action || payload.topic || "Sin contenido");
  formData.append("pqrs_type_id", payload.pqrs_type_id || "PETICION_GENERAL");
  formData.append("selected_dependency_id", payload.selected_dependency_id || "");
  formData.append("suggested_dependency_id", payload.suggested_dependency_id || "");
  formData.append("routing_confidence_score", String(payload.routing_confidence_score || 0));

  if (Array.isArray(payload.source_files) && payload.source_files.length > 0) {
    payload.source_files.forEach((file) => {
      formData.append("files", file);
    });
  } else if (payload.source_file) {
    formData.append("files", payload.source_file);
  }

  const response = await fetch(`${apiBaseUrl}/api/v1/citizen/submit`, {
    method: "POST",
    body: formData,
  });

  const body = await response.json();
  if (!response.ok) {
    throw new Error(body?.detail || `${response.status} ${response.statusText}`);
  }
  return body;
}
