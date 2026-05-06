import { useEffect, useMemo, useState } from "react";
import { fetchClosedLoopTelemetry } from "../services/governanceTelemetryApi";

const simulatedEvents = [
  { stage: "ingesta", value: 82, status: "healthy", totals: { OK: 1, PENDING: 0, ERROR: 0 } },
  { stage: "clasificacion", value: 96, status: "healthy", totals: { OK: 1, PENDING: 0, ERROR: 0 } },
  { stage: "auditoria_juridica", value: 91, status: "healthy", totals: { OK: 1, PENDING: 0, ERROR: 0 } },
  { stage: "firma_inmutable", value: 100, status: "healthy", totals: { OK: 1, PENDING: 0, ERROR: 0 } },
];

const fallbackReport = {
  total_records: 0,
  success_rate: 0,
  throughput_rps: 0,
  error_count: 0,
  latency_ms: { p50: 0, p95: 0, avg: 0, max: 0 },
};

export function useGovernanceStream(apiBaseUrl) {
  const [events, setEvents] = useState(simulatedEvents);
  const [connected, setConnected] = useState(false);
  const [timeline, setTimeline] = useState([]);
  const [report, setReport] = useState(fallbackReport);
  const [backendSummary, setBackendSummary] = useState({ maxValue: 100, alerts: 0, lastExternalId: null, lastStatus: null });
  const [telemetryError, setTelemetryError] = useState("");

  useEffect(() => {
    let active = true;

    const loadTelemetry = async () => {
      try {
        const payload = await fetchClosedLoopTelemetry(apiBaseUrl || import.meta.env.VITE_API_BASE_URL || "http://localhost:8000");
        if (!active) {
          return;
        }
        setEvents(Array.isArray(payload.events) && payload.events.length > 0 ? payload.events : simulatedEvents);
        setTimeline(Array.isArray(payload.timeline) ? payload.timeline : []);
        setReport(payload.report || fallbackReport);
        setConnected(Boolean(payload.summary?.connected));
        setBackendSummary(payload.summary || { maxValue: 100, alerts: 0, lastExternalId: null, lastStatus: null });
        setTelemetryError("");
      } catch (error) {
        if (!active) {
          return;
        }
        setConnected(false);
        setTelemetryError(error.message || "Telemetry unavailable");
        setEvents((current) =>
          current.map((event) => ({
            ...event,
            value: Math.max(72, Math.min(100, event.value + (Math.random() > 0.5 ? 2 : -2))),
          })),
        );
      }
    };

    loadTelemetry();
    const timer = window.setInterval(loadTelemetry, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [apiBaseUrl]);

  const summary = useMemo(
    () => ({
      connected,
      maxValue: backendSummary.maxValue ?? Math.max(...events.map((event) => event.value)),
      alerts: backendSummary.alerts ?? events.filter((event) => event.value < 80).length,
      lastExternalId: backendSummary.lastExternalId,
      lastStatus: backendSummary.lastStatus,
      report,
    }),
    [backendSummary, connected, events, report],
  );

  return { events, summary, timeline, report, telemetryError };
}