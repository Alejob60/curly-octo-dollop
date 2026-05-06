import { useRef, useState } from "react";
import { CheckCircle, FileText, Sparkles, TriangleAlert, UploadCloud, X } from "lucide-react";
import { useI18n } from "../i18n";
import { buildMockAutofill, evaluateIntegrity, hashFile } from "../utils/fileAudit";

function createInitialForm() {
  return {
    citizen_name: "",
    citizen_id: "",
    citizen_phone: "",
    citizen_email: "",
    citizen_address: "",
    topic: "",
    requested_action: "",
    pqrs_type_id: "",
    selected_dependency_id: "",
    suggested_dependency_id: "",
    routing_confidence_score: 0,
    manual_override: false,
  };
}

export function SmartUploader({
  onPrefill,
  statusLane,
  masterData,
  integrationConfig,
  integrationLoading,
  integrationResult,
  integrationError,
  onIntegrationConfigChange,
  onSuggestRouting,
  onSubmitToBackend,
}) {
  const { t } = useI18n();
  const fileInputRef = useRef(null);

  const [selectedFiles, setSelectedFiles] = useState([]);
  const [fileHash, setFileHash] = useState("");
  const [integrity, setIntegrity] = useState({ ok: false, score: 0 });
  const [formData, setFormData] = useState(createInitialForm);
  const [routingHint, setRoutingHint] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [extracted, setExtracted] = useState(false);

  const processFiles = async (files) => {
    if (!files?.length) return;
    setIsProcessing(true);
    setExtracted(false);
    setSelectedFiles(files);

    const firstFile = files[0];
    const nextHash = await hashFile(firstFile);
    setFileHash(nextHash);

    try {
      // 1. REAL-01: Subir el archivo al backend
      const formDataUpload = new FormData();
      formDataUpload.append("file", firstFile);
      
      const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      const response = await fetch(`${API_BASE}/api/v1/ingesta/upload`, {
        method: "POST",
        body: formDataUpload,
        headers: {
          "X-API-KEY": "orbital-prime-internal-key-2026" // Demo key
        }
      });

      if (!response.ok) throw new Error("Error en la subida del archivo");
      const { task_id } = await response.json();

      // 2. REAL-05: Polling al endpoint de tareas
      let taskStatus = "PENDING";
      let iaResult = null;

      while (taskStatus !== "SUCCESS" && taskStatus !== "FAILED") {
        await new Promise(resolve => setTimeout(resolve, 2000)); // Espera 2s
        
        const statusRes = await fetch(`${API_BASE}/api/v1/tasks/${task_id}`);
        const statusData = await statusRes.json();
        
        taskStatus = statusData.status;
        if (taskStatus === "SUCCESS") {
          iaResult = statusData.result;
        } else if (taskStatus === "FAILED") {
          throw new Error(statusData.error || "Error en el procesamiento de IA");
        }
      }

      // 3. Mapeo de datos REALES de Vertex AI
      if (iaResult) {
        const fillFields = {
          citizen_name: iaResult.nombre_completo || "",
          citizen_id: iaResult.numero_id || "",
          topic: iaResult.leyes_citadas?.join(", ") || "",
          requested_action: iaResult.resumen_hechos || "",
          suggested_dependency_id: iaResult.dependencia_sugerida || "",
          routing_confidence_score: iaResult.confidence_score || 0
        };

        setFormData((cur) => ({ 
          ...cur, 
          ...fillFields,
          selected_dependency_id: fillFields.suggested_dependency_id || cur.selected_dependency_id
        }));
        
        setRoutingHint({
          suggested_dependency_id: iaResult.dependencia_sugerida,
          confidence_score: iaResult.confidence_score,
          should_autoselect: true
        });
      }

      setIsProcessing(false);
      setExtracted(true);

    } catch (error) {
      console.error("Error en procesamiento real:", error);
      setIsProcessing(false);
      // Aquí podrías setear un error visible para el usuario
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = Array.from(e.dataTransfer?.files || []);
    if (files.length) {
      setSelectedFiles((current) => {
        const merged = [...current, ...files];
        processFiles(merged);
        return merged;
      });
    }
  };

  const removeFile = (indexToRemove) => {
    setSelectedFiles((current) => {
      const next = current.filter((_, index) => index !== indexToRemove);
      if (next.length === 0) {
        setExtracted(false);
        setFileHash("");
        setIntegrity({ ok: false, score: 0 });
      } else {
        processFiles(next);
      }
      return next;
    });
  };

  const handleFieldChange = (key, value) =>
    setFormData((cur) => ({ ...cur, [key]: value }));

  const handleDependencyChange = (value) =>
    setFormData((cur) => ({
      ...cur,
      selected_dependency_id: value,
      manual_override:
        Boolean(cur.suggested_dependency_id) && cur.suggested_dependency_id !== value,
    }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    const manualOverride =
      Boolean(formData.suggested_dependency_id) &&
      Boolean(formData.selected_dependency_id) &&
      formData.suggested_dependency_id !== formData.selected_dependency_id;

    const payload = {
      ...formData,
      manual_override: manualOverride,
      hash: fileHash,
      source_file_name: selectedFiles.map((file) => file.name).join(", ") || null,
    };

    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      const response = await fetch(`${API_BASE}/api/v1/citizen/radicar`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-KEY": "orbital-prime-internal-key-2026"
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error("Error en la radicación final");
      
      const result = await response.json();
      
      // Llamar a los callbacks del componente si existen
      onPrefill(payload);
      onSubmitToBackend(result);
      
    } catch (error) {
      console.error("Error en radicación final:", error);
    }
  };

  const confidencePct = routingHint ? Math.round((routingHint.confidence_score || 0) * 100) : 0;
  const suggestedDepName =
    masterData?.dependencies?.find((d) => d.id === formData.suggested_dependency_id)?.name ||
    routingHint?.suggested_dependency_name ||
    "";

  const inputCls =
    "w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-slate-800 text-sm shadow-sm transition focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100";
  const filledCls =
    "w-full rounded-lg border border-blue-200 bg-blue-50 px-3 py-2.5 text-slate-800 text-sm shadow-sm transition focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100";
  const labelCls = "block text-xs font-semibold uppercase tracking-wide text-slate-500 mb-1";

  return (
    <div className="max-w-5xl mx-auto bg-white shadow-2xl rounded-2xl border-t-[6px] border-indigo-600 overflow-hidden">
      {/* Header */}
      <div className="px-8 pt-7 pb-5 border-b border-slate-100">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-800">Radicaci&#243;n de PQRSD</h1>
            <p className="text-slate-500 text-sm mt-1">{t("smartForm.subtitle")}</p>
          </div>
          <span
            className={`mt-1 rounded-full px-3 py-1 text-xs font-bold uppercase tracking-widest ${
              statusLane === "green"
                ? "bg-green-100 text-green-700"
                : statusLane === "yellow"
                ? "bg-amber-100 text-amber-700"
                : "bg-red-100 text-red-700"
            }`}
          >
            {statusLane}
          </span>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="px-8 py-6 space-y-6">
        {/* DROP ZONE */}
        <div
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          className={`relative cursor-pointer rounded-xl border-2 border-dashed py-10 text-center transition-all select-none ${
            isDragOver
              ? "border-indigo-400 bg-indigo-50"
              : isProcessing
              ? "border-blue-300 bg-blue-50"
              : extracted
              ? "border-green-300 bg-green-50"
              : "border-slate-300 bg-slate-50 hover:border-indigo-400 hover:bg-indigo-50"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            accept=".pdf,.jpg,.jpeg,.png"
            onChange={(e) => {
              const files = Array.from(e.target.files || []);
              if (!files.length) {
                return;
              }
              setSelectedFiles((current) => {
                const merged = [...current, ...files];
                processFiles(merged);
                return merged;
              });
            }}
          />
          {isProcessing ? (
            <div className="flex flex-col items-center gap-2 animate-pulse">
              <Sparkles className="w-10 h-10 text-blue-500 animate-spin" />
              <p className="font-bold text-blue-700 text-base">{t("smartForm.processing")}</p>
              <p className="text-xs text-blue-400">{t("smartForm.processingHint")}</p>
            </div>
          ) : extracted ? (
            <div className="flex flex-col items-center gap-2">
              <CheckCircle className="w-10 h-10 text-green-500" />
              <p className="font-bold text-green-700 text-base">{t("smartForm.extractedTitle")}</p>
              <p className="text-xs text-green-500">
                {selectedFiles.length > 1
                  ? `${selectedFiles.length} ${t("smartForm.filesAttached")}`
                  : selectedFiles?.[0]?.name}
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <UploadCloud className="w-10 h-10 text-slate-400" />
              <p className="font-bold text-slate-700 text-base">{t("smartForm.dropTitle")}</p>
              <p className="text-xs text-slate-400">{t("smartForm.dropHint")}</p>
            </div>
          )}
        </div>

        {selectedFiles.length > 0 && (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p className="mb-3 text-sm font-semibold text-slate-700">
              {t("smartForm.attachmentsTitle")} ({selectedFiles.length})
            </p>
            <div className="space-y-2">
              {selectedFiles.map((file, index) => (
                <div
                  key={`${file.name}-${index}`}
                  className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-2"
                >
                  <div className="flex min-w-0 items-center gap-2 text-slate-600">
                    <FileText className="h-4 w-4 shrink-0 text-indigo-500" />
                    <span className="truncate text-sm">{file.name}</span>
                    <span className="shrink-0 text-xs text-slate-400">
                      ({(file.size / 1024).toFixed(1)} KB)
                    </span>
                  </div>
                  <button
                    className="text-red-400 transition hover:text-red-600"
                    onClick={() => removeFile(index)}
                    type="button"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* AI banner */}
        {extracted && routingHint && (
          <div className="flex items-start gap-3 rounded-xl border-l-4 border-indigo-500 bg-indigo-50 px-4 py-3">
            <Sparkles className="w-5 h-5 mt-0.5 text-indigo-600 flex-shrink-0" />
            <div className="min-w-0">
              <p className="font-bold text-indigo-800 text-sm">{t("smartForm.aiSuccessBanner")}</p>
              <p className="text-indigo-600 text-xs mt-0.5">
                {t("smartForm.aiSuccessDetail")
                  .replace("{type}", masterData?.pqrs_types?.find((p) => p.id === formData.pqrs_type_id)?.name || "Petici\u00f3n")
                  .replace("{dep}", suggestedDepName)}
              </p>
            </div>
            <span className="ml-auto flex-shrink-0 rounded-full bg-indigo-600 px-2.5 py-0.5 text-xs font-bold text-white">
              {confidencePct}%
            </span>
          </div>
        )}

        {/* Integrity warning */}
        {extracted && !integrity.ok && (
          <div className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
            <TriangleAlert className="w-4 h-4 flex-shrink-0" />
            {t("uploader.integrityWarn")}
          </div>
        )}

        {/* Form grid — dims until file uploaded */}
        <div className={`transition-opacity duration-500 ${extracted ? "opacity-100" : "opacity-35 pointer-events-none"}`}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Personal data */}
            <div className="space-y-4">
              <h3 className="font-bold text-slate-700 border-b border-slate-100 pb-2 text-xs uppercase tracking-widest">
                {t("smartForm.sectionPersonal")}
              </h3>
              {[
                ["citizen_name", t("uploader.citizenName"), "text"],
                ["citizen_id", t("uploader.citizenId"), "text"],
                ["citizen_phone", t("uploader.citizenPhone"), "text"],
                ["citizen_email", t("uploader.citizenEmail"), "email"],
                ["citizen_address", t("uploader.citizenAddress"), "text"],
              ].map(([key, label, type]) => (
                <div key={key}>
                  <label className={labelCls}>{label}</label>
                  <input
                    type={type}
                    className={formData[key] ? filledCls : inputCls}
                    value={formData[key] || ""}
                    onChange={(e) => handleFieldChange(key, e.target.value)}
                    placeholder={label}
                  />
                </div>
              ))}
            </div>

            {/* Classification */}
            <div className="space-y-4">
              <h3 className="font-bold text-slate-700 border-b border-slate-100 pb-2 text-xs uppercase tracking-widest">
                {t("smartForm.sectionClassification")}
              </h3>

              <div>
                <label className={labelCls}>{t("uploader.category")}</label>
                <select
                  className={inputCls}
                  value={formData.pqrs_type_id}
                  onChange={(e) => handleFieldChange("pqrs_type_id", e.target.value)}
                >
                  <option value="">{t("uploader.selectCategory")}</option>
                  {(masterData?.pqrs_types || []).map((item) => (
                    <option key={item.id} value={item.id}>{item.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className={labelCls}>{t("uploader.department")}</label>
                <select
                  className={
                    formData.suggested_dependency_id
                      ? "w-full rounded-lg border-2 border-indigo-400 bg-indigo-50 px-3 py-2.5 text-indigo-900 font-semibold text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-200"
                      : inputCls
                  }
                  value={formData.selected_dependency_id}
                  onChange={(e) => handleDependencyChange(e.target.value)}
                >
                  <option value="">{t("uploader.selectDependency")}</option>
                  {(masterData?.dependencies || []).map((item) => (
                    <option key={item.id} value={item.id}>{item.name}</option>
                  ))}
                </select>
                {routingHint && (
                  <p className="mt-1 text-xs text-indigo-600 font-medium flex items-center gap-1">
                    <Sparkles className="w-3 h-3" />
                    {t("smartForm.aiRouted")} {confidencePct}% {t("smartForm.confidence")}
                  </p>
                )}
                {formData.manual_override && (
                  <p className="mt-1 text-xs text-amber-600">{t("smartForm.manualOverrideNote")}</p>
                )}
              </div>

              <div>
                <label className={labelCls}>{t("uploader.topic")}</label>
                <input
                  className={formData.topic ? filledCls : inputCls}
                  value={formData.topic}
                  onChange={(e) => handleFieldChange("topic", e.target.value)}
                  placeholder={t("uploader.topic")}
                />
              </div>
            </div>
          </div>

          {/* Facts textarea */}
          <div className="mt-5">
            <label className={labelCls}>{t("smartForm.factsLabel")}</label>
            <textarea
              rows={4}
              className={`${formData.requested_action ? filledCls : inputCls} min-h-[5.5rem] resize-y`}
              value={formData.requested_action}
              onChange={(e) => handleFieldChange("requested_action", e.target.value)}
              placeholder={t("smartForm.factsPlaceholder")}
            />
            {formData.requested_action && (
              <p className="mt-1 flex items-center gap-1 text-xs text-blue-500">
                <Sparkles className="w-3 h-3" /> {t("smartForm.aiExtractedFacts")}
              </p>
            )}
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={integrationLoading}
            className="mt-6 w-full rounded-xl bg-indigo-600 py-3.5 text-sm font-bold uppercase tracking-widest text-white shadow-lg transition hover:bg-indigo-700 hover:-translate-y-0.5 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {integrationLoading ? t("integration.submitting") : t("smartForm.submitBtn")}
          </button>
        </div>

        {/* Result */}
        {integrationResult && (
          <div className="rounded-xl border border-green-200 bg-green-50 p-4">
            <p className="font-bold text-green-800 text-sm mb-2">{t("smartForm.resultTitle")}</p>
            <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
              <div>
                <span className="font-semibold text-slate-500">{t("integration.resultId")}:</span>
                <span className="ml-2 font-bold text-indigo-700 text-base">{integrationResult.radicado}</span>
              </div>
              <div>
                <span className="font-semibold text-slate-500">{t("integration.resultPdf")}:</span>
                <span className="ml-2">{integrationResult.message}</span>
              </div>
            </div>
          </div>
        )}

        {/* Error */}
        {integrationError && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {integrationError}
          </div>
        )}
      </form>
    </div>
  );
}
