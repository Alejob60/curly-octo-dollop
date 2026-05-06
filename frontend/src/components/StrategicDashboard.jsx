import { useState, useEffect } from "react";
import { useI18n } from "../i18n";
import { BarChart3, TrendingUp, ShieldAlert, Zap, Globe, MapPin, Smile, Frown, Meh, ArrowUpRight, Clock, ShieldCheck, Activity, ChevronRight, BadgeCheck } from "lucide-react";

export function StrategicDashboard() {
  const { t } = useI18n();
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    const fetchSummary = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/dashboard/summary`, {
            headers: { "Authorization": `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await res.json();
        setSummary(data);
      } catch (e) {
        console.error("Error fetching summary:", e);
      }
    };
    fetchSummary();
    const interval = setInterval(fetchSummary, 30000);
    return () => clearInterval(interval);
  }, []);

  const metrics = [
    { label: "Cumplimiento SLA", value: `${summary?.kpis?.compliance_rate || 92.4}%`, icon: ShieldCheck, trend: "+2.1%", color: "text-emerald-600", bg: "bg-emerald-50" },
    { label: "Tiempo Promedio", value: `${summary?.kpis?.avg_response_days || 3.8} d`, icon: Clock, trend: "-12%", color: "text-indigo-600", bg: "bg-indigo-50" },
    { label: "Créditos IA Usados", value: (summary?.kpis?.ai_credits_used || 1540).toLocaleString(), icon: Zap, trend: "Plan Gov", color: "text-blue-600", bg: "bg-blue-50" },
    { label: "Radicados Activos", value: (summary?.kpis?.total_active || 48).toLocaleString(), icon: Activity, trend: "Real-time", color: "text-rose-600", bg: "bg-rose-50" }
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-12 animate-in fade-in duration-700 pb-20 p-8 bg-white/50 min-h-screen">
      {/* HEADER DE ALTO NIVEL - OJO DE HALCÓN */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-slate-100 pb-10">
        <div>
          <div className="flex items-center gap-2 mb-2">
             <span className="px-2 py-0.5 rounded bg-slate-900 text-white text-[10px] font-black uppercase tracking-widest">Ojo de Halcón BI</span>
             <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div> Sincronizado con Despacho del Alcalde
             </span>
          </div>
          <h2 className="text-4xl font-black tracking-tighter text-slate-900">{t("strategic.title")}</h2>
          <p className="text-slate-500 font-medium text-lg max-w-2xl italic">Control y Auditoría Transversal de la Burocracia Distrital</p>
        </div>
        <button className="px-8 py-3 bg-slate-900 text-white rounded-2xl font-bold text-sm hover:scale-105 transition-all shadow-xl shadow-slate-200">
           {t("dashboard.exportPdf")}
        </button>
      </div>

      {/* KPI GRID */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {metrics.map((m, i) => (
          <div key={i} className="bg-white border border-slate-100 p-8 rounded-[2.5rem] shadow-sm hover:shadow-2xl hover:border-slate-200 transition-all group relative overflow-hidden">
            <div className={`p-4 rounded-2xl w-fit ${m.bg} ${m.color} mb-6 group-hover:scale-110 transition-transform`}>
              <m.icon className="w-6 h-6" />
            </div>
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">{m.label}</p>
            <div className="flex items-end gap-3 mt-2">
              <h3 className="text-3xl font-black text-slate-900">{m.value}</h3>
              <span className={`text-xs font-bold mb-1 px-2 py-0.5 rounded-full ${m.trend.startsWith('+') ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-500'}`}>
                {m.trend}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* RASTREADOR MULTIDEPENDENCIA V20 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
         <div className="lg:col-span-2 bg-slate-900 rounded-[3.5rem] p-12 text-white shadow-2xl relative overflow-hidden">
            <div className="relative z-10 space-y-10">
               <div className="flex items-center justify-between">
                  <div className="space-y-2">
                    <h3 className="text-2xl font-black tracking-tight flex items-center gap-3">
                        <Activity className="w-6 h-6 text-emerald-400" /> Rastreador de Casos Críticos
                    </h3>
                    <p className="text-white/40 text-sm font-medium">Auditoría en tiempo real de radicados transversales</p>
                  </div>
                  <div className="px-4 py-2 bg-rose-500/20 border border-rose-500/40 rounded-2xl text-rose-400 text-[10px] font-black uppercase tracking-widest animate-pulse">Riesgo Silencio Administrativo</div>
               </div>

               {/* ÁRBOL DE RESOLUCIÓN MULTIDEPENDENCIA */}
               <div className="space-y-6">
                  <div className="bg-white/5 border border-white/10 p-8 rounded-[2.5rem] space-y-8">
                     <div className="flex items-center justify-between border-b border-white/5 pb-6">
                        <div className="flex items-center gap-4">
                           <div className="w-12 h-12 bg-indigo-500 rounded-2xl flex items-center justify-center font-black text-xl">M</div>
                           <div>
                              <p className="text-lg font-black tracking-tight">RAD-2026-MURC-001</p>
                              <p className="text-xs text-white/40 uppercase font-bold tracking-widest">Invasión Murciélagos I.E. La Merced</p>
                           </div>
                        </div>
                        <div className="text-right">
                           <p className="text-sm font-black text-amber-400 uppercase tracking-widest">4 DÍAS RESTANTES</p>
                           <p className="text-[10px] text-white/20 font-bold">Vencimiento: 25/04/2026</p>
                        </div>
                     </div>
                     
                     <div className="grid grid-cols-3 gap-8 py-4 relative">
                        {/* Línea conectora */}
                        <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-white/5 -translate-y-6"></div>
                        
                        {[
                           { label: "Educación", status: "OK", color: "bg-emerald-500", desc: "Presupuesto Aprobado" },
                           { label: "Salud", status: "OK", color: "bg-emerald-500", desc: "Inspección Finalizada" },
                           { label: "DAGMA", status: "PENDIENTE", color: "bg-rose-500 animate-pulse", desc: "Esperando Biólogo" }
                        ].map((node, i) => (
                           <div key={i} className="flex flex-col items-center gap-4 relative z-10">
                              <div className={`w-4 h-4 rounded-full ${node.color} border-4 border-slate-900 shadow-[0_0_15px_rgba(244,63,94,0.3)]`}></div>
                              <div className="text-center">
                                 <p className="text-[10px] font-black uppercase tracking-widest text-white/80">{node.label}</p>
                                 <p className="text-[9px] text-white/30 font-bold mt-1 uppercase">{node.desc}</p>
                              </div>
                           </div>
                        ))}
                     </div>
                     
                     <button className="w-full mt-4 py-4 bg-rose-600 hover:bg-rose-700 text-white rounded-2xl text-xs font-black uppercase tracking-[0.2em] transition-all shadow-2xl flex items-center justify-center gap-3">
                        <ShieldAlert className="w-4 h-4" /> Emitir Requerimiento Perentorio a DAGMA
                     </button>
                  </div>
               </div>
            </div>
            <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-600/10 blur-[120px] -mr-48 -mt-48"></div>
         </div>

         <div className="bg-white border border-slate-100 rounded-[3.5rem] p-10 shadow-sm space-y-10 flex flex-col justify-between">
            <div>
               <h3 className="text-xl font-black text-slate-900 tracking-tight flex items-center gap-3">
                  <TrendingUp className="w-5 h-5 text-indigo-600" /> Ranking de Eficiencia
               </h3>
               <div className="space-y-8 mt-10">
                  {(summary?.efficiency_ranking || [
                      { label: "Hacienda", total: 18 },
                      { label: "Educación", total: 15 },
                      { label: "Dagma", total: 6 },
                      { label: "Movilidad", total: 4 }
                  ]).map((node, i) => (
                     <div key={i} className="space-y-3">
                        <div className="flex justify-between text-[11px] font-black uppercase tracking-widest text-slate-400">
                           <span>{node.label}</span>
                           <span className="text-slate-900">{node.total} resolved</span>
                        </div>
                        <div className="h-2 bg-slate-50 rounded-full overflow-hidden">
                           <div className="h-full bg-indigo-500 rounded-full transition-all duration-1000" style={{ width: `${(node.total / 20) * 100}%` }}></div>
                        </div>
                     </div>
                  ))}
               </div>
            </div>
            
            <div className="pt-8 border-t border-slate-50 space-y-4">
                <div className="p-6 bg-emerald-50 rounded-[2rem] border border-emerald-100">
                    <p className="text-[11px] text-emerald-800 font-black leading-relaxed uppercase tracking-tight">
                       ✨ Impacto Social: 2,4k ciudadanos atendidos por la IA este mes.
                    </p>
                </div>
            </div>
         </div>
      </div>
      
      {/* FOOTER ANALYTICS */}
      <div className="pt-10 flex items-center justify-between border-t border-slate-100">
         <p className="text-[10px] font-black text-slate-300 uppercase tracking-[0.3em]">Orbital Prime Strategic Intel V20 · Cali Smart City</p>
         <div className="flex items-center gap-8">
            <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-emerald-500"></div> <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Oracle DB Native Sync</span></div>
            <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-indigo-500"></div> <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Gemini 2.0 BI Engine</span></div>
         </div>
      </div>
    </div>
  );
}
