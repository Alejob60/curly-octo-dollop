export async function hashFile(file) {
  const buffer = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(digest))
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}

export function buildMockAutofill(file, t) {
  const name = file.name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " ");
  return {
    citizen_name: t("uploader.mockCitizenName"),
    citizen_email: t("uploader.mockCitizenEmail"),
    citizen_address: t("uploader.mockCitizenAddress"),
    topic: name || t("uploader.mockInstitutionalRequest"),
    requested_action: t("uploader.mockRequestedAction"),
    category: t("uploader.defaultCategory"),
    department: t("uploader.defaultDepartment"),
    ocrPreview: t("uploader.mockOcrPreview").replace("{file}", file.name),
  };
}

export function evaluateIntegrity(file) {
  if (!file) {
    return { ok: false, score: 0 };
  }

  const sizeScore = file.size > 1024 ? 0.55 : 0.25;
  const formatScore = /(pdf|png|jpg|jpeg)$/i.test(file.name) ? 0.35 : 0.15;
  const nameScore = file.name.length > 8 ? 0.1 : 0.05;
  const score = Number((sizeScore + formatScore + nameScore).toFixed(2));

  return {
    ok: score >= 0.8,
    score,
  };
}