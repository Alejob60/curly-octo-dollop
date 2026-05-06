import React, { useState, useEffect } from "react";
import { useI18n } from "../i18n";
import { 
  LayoutDashboard, Activity, ShieldCheck, Building2, Globe, MoreVertical,
  Gavel, CheckCircle2, Zap
} from "lucide-react";
import { useGovernanceStore } from "../store/useGovernanceStore";
import GlobalFilters from "./dashboard/GlobalFilters";
import CaseQueue from "./dashboard/CaseQueue";

export function GovernanceDashboard({ isConnected }) {
  const { t } = useI18n();
  const { selectedCase, selectCase, updateCases } = useGovernanceStore();
  const [selectedDep, setSelectedDep] = useState("GLOBAL"); 
  const [checklist, setChecklist] = useState({ competencia: false, pruebas: false, grounding: false, congruencia: false });
  const [masterAction, setMasterAction] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  const dependencias = [
    { id: "4145010", name: "Infraestructura", color: "bg-blue-600" },
    { id: "4145020", name: "Movilidad", color: "bg-amber-500" },
    { id: "4145030", name: "Salud Pública", color: "bg-emerald-600" },
    { id: "4145040", name: "Seguridad y Justicia", color: "bg-rose-600" },
    { id: "4145050", name: "Dagma", color: "bg-green-600" },
    { id: "4145060", name: "Educación", color: "bg-indigo-600" },
    { id: "4145070", name: "Hacienda", color: "bg-slate-700" }
  ];

  useEffect(() => { 
    const fetchCases = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/v1/pqrs/governance/cases`);
        const data = await res.json();
        if (data.status === 'success') {
          // Adaptamos el formato del backend al formato del Store V1.0
          const adaptedCases = data.cases.map(c => ({
            radicado: c.id,
            citizenName: "ALEJANDRO", // Placeholder hasta tener rehidratación en lista
            dependencyId: c.dependencia,
            dependencyName: c.dependencia,
            confidence: Math.round(c.ai_score * 100),
            riskLevel: c.risk_level,
            slaRemaining: 24,
            createdAt: c.fecha,
            asunto: c.asunto
          }));
          updateCases(adaptedCases);
        }
      } catch (e) { console.error(e); }
    };
    fetchCases(); 
  }, [updateCases]);

  const handleDecision = async (action) => {
    if (!selectedCase) return;
    setIsProcessing(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/pqrs/governance/review/${selectedCase.radicado}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, comments: "Supervisor Maestro: Resolución confirmada.", official_id: "ADMIN-MASTER" })
      });
      const result = await response.json();
      if (result.status === 'success') { 
        alert(result.message); 
        selectCase(null); 
      }
    } catch (e) { console.error(e); } finally { setIsProcessing(false); }
  };

  const getDynamicActions = (dep) => {
    const d = dep?.toLowerCase() || "";
    if (d.includes("salud")) return [{ id: "ipu", label: "Traslado IPS", desc: "Urgente" }, { id: "auditoria", label: "Auditoría Médica", desc: "Validación" }];
    if (d.includes("infra")) return [{ id: "obra", label: "Plan Bacheo", desc: "Programación" }, { id: "visita", label: "Inspección", desc: "Campo" }];
    return [{ id: "tramite", label: "Trámite Ley 1755", desc: "Estándar" }, { id: "traslado", label: "Traslado Externo", desc: "Competencia" }];
  };

  return (
    <div className="flex h-[calc(100vh-120px)] w-full bg-[#F1F5F9] rounded-[2.5rem] border border-slate-200 overflow-hidden shadow-2xl">
      
      {/* SIDEBAR */}
      <aside className="w-64 bg-[#0A2540] text-white flex flex-col border-r border-white/10 shrink-0">
        <div className="p-6 border-b border-white/5 bg-white/5">
          <div className="flex items-center gap-2 mb-6">
            <Building2 className="w-4 h-4 text-indigo-400" />
            <h2 className="text-[10px] font-black uppercase tracking-widest text-indigo-100">Cali Digital</h2>
          </div>
          <button onClick={() => setSelectedDep("GLOBAL")} className={`w-full flex items-center gap-3 p-3 rounded-xl mb-4 transition-all border-2 ${selectedDep === "GLOBAL" ? 'bg-indigo-600 border-indigo-400 shadow-xl' : 'bg-white/5 border-transparent hover:bg-white/10'}`}>
            <Globe className="w-4 h-4" />
            <span className="text-[10px] font-black uppercase">Vista Maestro</span>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
          {dependencias.map(dep => (
            <button key={dep.id} onClick={() => setSelectedDep(dep.id)} className={`w-full flex items-center p-2.5 rounded-xl transition-all ${selectedDep === dep.id ? 'bg-white/10 border-l-4 border-l-indigo-500' : 'hover:bg-white/5'}`}>
              <div className={`w-1.5 h-1.5 rounded-full mr-3 ${dep.color}`} />
              <span className="text-[9px] font-bold text-white/70">{dep.name}</span>
            </button>
          ))}
        </div>
      </aside>

      {/* WORKSPACE PRINCIPAL */}
      <div className="flex-1 flex flex-col overflow-hidden bg-white">
        
        {/* FILTROS GLOBALES V1.0 */}
        <GlobalFilters />

        {/* HEADER */}
        <header className="p-6 bg-white border-b border-slate-100 flex justify-between items-center shrink-0">
          <div className="flex items-center gap-4">
            <div className="p-2 bg-slate-100 rounded-lg"><LayoutDashboard className="w-5 h-5 text-slate-600" /></div>
            <h1 className="text-xl font-black text-slate-900 tracking-tighter uppercase">Supervisión Híbrida V1.0</h1>
          </div>
          <div className="flex gap-2">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-full text-[9px] font-black border border-emerald-100"><ShieldCheck className="w-3 h-3" /> Audit Active</div>
          </div>
        </header>

        {/* COLA DE CASOS DINÁMICA */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-50/30 custom-scrollbar">
           <CaseQueue />
        </div>
      </div>

      {/* PANEL DE GESTIÓN (Derecha) */}
      {selectedCase && (
        <aside className="w-[450px] bg-white border-l border-slate-200 flex flex-col overflow-hidden animate-in slide-in-from-right duration-300">
          <header className="p-6 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
            <div>
               <h2 className="text-sm font-black text-slate-900 tracking-tighter uppercase">{selectedCase.radicado}</h2>
               <p className="text-[8px] font-bold text-indigo-600 uppercase">{selectedCase.dependencyName}</p>
            </div>
            <button onClick={() => selectCase(null)} className="text-slate-400 hover:text-slate-900"><MoreVertical className="w-5 h-5" /></button>
          </header>
          
          <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
            {/* ACCIONES DINÁMICAS */}
            <section className="bg-slate-50 border border-slate-200 rounded-2xl p-4">
              <h3 className="text-[9px] font-black text-slate-400 uppercase mb-4 flex items-center gap-2"><Gavel className="w-3.5 h-3.5 text-indigo-600" /> Acción Sugerida</h3>
              <div className="space-y-2">
                {getDynamicActions(selectedCase.dependencyName).map(act => (
                  <label key={act.id} className={`flex items-center gap-3 p-3 rounded-xl border-2 transition-all cursor-pointer ${masterAction === act.id ? 'border-indigo-600 bg-white shadow-md' : 'bg-white/50 border-transparent hover:border-slate-300'}`}>
                    <input type="radio" checked={masterAction === act.id} onChange={() => setMasterAction(act.id)} className="accent-indigo-600" />
                    <div>
                      <p className="text-[10px] font-black text-slate-800 uppercase leading-none">{act.label}</p>
                      <p className="text-[8px] text-slate-400 mt-0.5">{act.desc}</p>
                    </div>
                  </label>
                ))}
              </div>
            </section>

            {/* CHECKLIST */}
            <section className="bg-slate-900 rounded-2xl p-6 text-white shadow-xl">
               <h3 className="text-[9px] font-black text-indigo-300 uppercase mb-4 flex items-center gap-2"><ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Verificación Legal</h3>
               <div className="space-y-3">
                 {['competencia', 'pruebas', 'grounding', 'congruencia'].map(k => (
                   <div key={k} onClick={() => setChecklist({...checklist, [k]: !checklist[k]})} className="flex items-center justify-between cursor-pointer group">
                      <span className={`text-[9px] font-bold ${checklist[k] ? 'text-emerald-400' : 'text-white/30 group-hover:text-white/50'}`}>{k.toUpperCase()} VERIFICADO</span>
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${checklist[k] ? 'bg-emerald-500 border-emerald-500' : 'border-white/10'}`}>
                        {checklist[k] && <CheckCircle2 className="w-3 h-3" />}
                      </div>
                   </div>
                 ))}
               </div>
            </section>

            {/* PROYECCIÓN IA */}
            <section className="bg-[#FDFCF8] border border-slate-200 rounded-2xl p-5 shadow-inner">
               <h3 className="text-[9px] font-black text-slate-400 uppercase mb-3 flex items-center gap-2"><Zap className="w-3.5 h-3.5 text-indigo-600" /> Borrador de Fondo</h3>
               <p className="text-[11px] font-serif italic text-slate-600 leading-relaxed overflow-y-auto max-h-40">
                 {selectedCase.asunto}
               </p>
            </section>
          </div>

          <div className="p-6 border-t border-slate-100 bg-white">
            <button 
              disabled={!masterAction || isProcessing}
              onClick={() => handleDecision("approve")}
              className={`w-full py-4 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all shadow-xl ${masterAction ? 'bg-slate-900 text-white hover:bg-indigo-600' : 'bg-slate-100 text-slate-300'}`}
            >
              {isProcessing ? "Firmando Expediente..." : "Firmar Resolución"}
            </button>
          </div>
        </aside>
      )}
    </div>
  );
}
