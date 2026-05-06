import { useState, useEffect } from "react";
import { useI18n } from "../i18n";
import { Search, Filter, Clock, CheckCircle2, AlertTriangle, FileText, ChevronRight, X, Sparkles, Map as MapIcon, User as UserIcon, Scale } from "lucide-react";

export function LegalReviewQueue() {
  const { t } = useI18n();
  const [tasks, setTasks] = useState([]);
  const [filter, setFilter] = useState("all");
  const [selectedTask, setSelectedTask] = useState(null);
  const [isProjecting, setIsProcessing] = useState(false);
  const [draftResult, setDraftResult] = useState("");

  const dependencyId = 4158; // Hacienda Default for Demo

  useEffect(() => {
    const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const fetchTasks = async () => {
        try {
            const response = await fetch(`${API_BASE}/api/v1/dashboard/tracking/${dependencyId}`, {
                headers: { "Authorization": `Bearer ${localStorage.getItem('token')}` }
            });
            const data = await response.json();
            setTasks(data.items || []);
        } catch (e) {
            console.error("Error fetching tasks:", e);
        }
    };
    fetchTasks();
    const interval = setInterval(fetchTasks, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleGenerateDraft = async (taskId) => {
    setIsProcessing(true);
    try {
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/staff/generate-draft`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "Authorization": `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({ radicado_id: taskId, notes: "Analizar peticion bajo Ley 1755" })
        });
        const data = await response.json();
        setDraftResult(data.draft);
    } catch (e) {
        console.error(e);
    } finally {
        setIsProcessing(false);
    }
  };

  const displayTasks = tasks.length > 0 ? tasks : [
      { id: 99, codigo: "CALI-2026-WOW-A37C", citizen: "Alejandro Benavides", tipo: "Reclamo Predial", semaforo: "red", progreso_label: "12 días" },
      { id: 100, codigo: "CALI-2026-MOV-055", citizen: "Luis E. Chaves", tipo: "Nulidad Multa", semaforo: "green", progreso_label: "8 días" }
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-700 relative">
      {/* CASE DETAILS MODAL */}
      {selectedTask && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-6">
            <div className="bg-white rounded-[2.5rem] shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in-95 duration-300">
                <div className="p-8 border-b border-slate-100 flex items-center justify-between">
                    <div>
                        <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1 block">Expediente Administrativo</span>
                        <h3 className="text-2xl font-black text-slate-900">{selectedTask.codigo}</h3>
                    </div>
                    <button onClick={() => { setSelectedTask(null); setDraftResult(""); }} className="p-3 bg-slate-50 rounded-2xl hover:bg-slate-100 transition-all">
                        <X className="w-5 h-5 text-slate-400" />
                    </button>
                </div>
                
                <div className="flex-1 overflow-y-auto p-10 grid grid-cols-1 md:grid-cols-2 gap-12">
                    <div className="space-y-8">
                        <section className="space-y-4">
                            <div className="flex items-center gap-2 text-indigo-600">
                                <UserIcon className="w-4 h-4" />
                                <h4 className="text-xs font-black uppercase tracking-widest">Peticionario</h4>
                            </div>
                            <p className="text-sm font-bold text-slate-800">{selectedTask.citizen || "Cargando..."}</p>
                        </section>

                        <section className="space-y-4">
                            <div className="flex items-center gap-2 text-rose-600">
                                <MapIcon className="w-4 h-4" />
                                <h4 className="text-xs font-black uppercase tracking-widest">Georreferenciación</h4>
                            </div>
                            <div className="aspect-video bg-slate-100 rounded-2xl border-2 border-dashed border-slate-200 flex items-center justify-center">
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Mapa Satelital Real</p>
                            </div>
                        </section>

                        <section className="space-y-4">
                            <div className="flex items-center gap-2 text-emerald-600">
                                <FileText className="w-4 h-4" />
                                <h4 className="text-xs font-black uppercase tracking-widest">Hechos y Pretensiones</h4>
                            </div>
                            <p className="text-sm text-slate-600 leading-relaxed bg-slate-50 p-4 rounded-2xl border border-slate-100">
                               Análisis automático del relato ciudadano completado. El expediente cuenta con suficiencia fáctica.
                            </p>
                        </section>
                    </div>

                    <div className="space-y-6">
                        <div className="p-6 bg-slate-900 rounded-3xl text-white space-y-6 shadow-xl">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 text-emerald-400">
                                    <Sparkles className="w-4 h-4" />
                                    <h4 className="text-xs font-black uppercase tracking-widest">Misybot Projection</h4>
                                </div>
                                <span className="text-[9px] bg-white/10 px-2 py-1 rounded-md text-white/40">1 CRÉDITO IA</span>
                            </div>
                            
                            {draftResult ? (
                                <div className="text-sm font-medium leading-relaxed prose prose-invert max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                                    {draftResult.split('\n').map((line, i) => <p key={i}>{line}</p>)}
                                </div>
                            ) : (
                                <p className="text-sm text-white/40 italic">Utilice la IA para proyectar una respuesta motivada citando el CPACA.</p>
                            )}

                            <button 
                                onClick={() => handleGenerateDraft(selectedTask.codigo)}
                                disabled={isProjecting}
                                className="w-full py-4 bg-white text-slate-900 rounded-2xl text-xs font-black uppercase tracking-widest hover:bg-emerald-400 hover:text-white transition-all flex items-center justify-center gap-2 shadow-2xl"
                            >
                                {isProjecting ? <Sparkles className="w-4 h-4 animate-spin" /> : <Scale className="w-4 h-4" />}
                                {isProjecting ? 'Generando...' : 'Proyectar Respuesta'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
      )}

      {/* HEADER MINIMALISTA */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-slate-100 pb-8">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-slate-900">{t("legalDesk.title")}</h2>
          <p className="text-slate-500 mt-1">{t("legalDesk.subtitle")}</p>
        </div>
        <div className="flex items-center gap-3">
           <div className="px-4 py-2 bg-indigo-50 text-indigo-600 rounded-xl text-xs font-black uppercase tracking-widest">
              Dependencia: {dependencyId}
           </div>
        </div>
      </div>

      {/* LISTA DE TAREAS */}
      <div className="space-y-4">
        {displayTasks.map((task) => (
          <article 
            key={task.id}
            onClick={() => setSelectedTask(task)}
            className="group cursor-pointer bg-white border border-slate-100 hover:border-slate-300 hover:shadow-xl hover:shadow-slate-200/40 p-5 rounded-[1.5rem] transition-all duration-300 flex items-center justify-between"
          >
            <div className="flex items-center gap-6">
              <div className={`p-4 rounded-2xl ${task.semaforo === 'red' ? 'bg-rose-50' : 'bg-slate-50'}`}>
                <FileText className={`w-6 h-6 ${task.semaforo === 'red' ? 'text-rose-500' : 'text-slate-400'}`} />
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono font-bold text-slate-400 tracking-tighter">{task.codigo}</span>
                  {task.semaforo === 'red' && (
                    <span className="px-2 py-0.5 rounded-md bg-rose-100 text-rose-600 text-[10px] font-bold uppercase tracking-wider animate-pulse">
                       Urgente
                    </span>
                  )}
                </div>
                <h3 className="text-base font-bold text-slate-800 mt-0.5">{task.tipo}</h3>
                <p className="text-sm text-slate-500">{t("legalDesk.citizenLabel")}: <span className="font-medium text-slate-700">{task.citizen || 'Anónimo'}</span></p>
              </div>
            </div>

            <div className="flex items-center gap-10">
              <div className="text-right">
                <div className="flex items-center justify-end gap-1.5 text-slate-400">
                  <Clock className="w-3.5 h-3.5" />
                  <span className="text-xs font-bold uppercase tracking-widest">Estado</span>
                </div>
                <p className={`text-sm font-bold mt-0.5 ${task.semaforo === 'red' ? 'text-rose-500' : 'text-slate-700'}`}>
                  {task.progreso_label}
                </p>
              </div>
              
              <button className="flex items-center gap-2 px-5 py-2.5 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all shadow-lg">
                 Atender <ChevronRight className="w-4 h-4 opacity-50" />
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
