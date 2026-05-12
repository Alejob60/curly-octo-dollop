import React, { useState, useEffect } from 'react';
import { ShieldAlert, Scale, CheckCircle, XCircle, ChevronRight, Search, Filter, AlertCircle, Info, Download } from 'lucide-react';

export const HumanReviewTray = () => {
    const [reviews, setReviews] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedCase, setSelectedTask] = useState(null);

    useEffect(() => {
        const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
        const fetchReviews = async () => {
            try {
                // Endpoint para obtener casos que requieren revisión humana
                const res = await fetch(`${API_BASE}/api/v1/metrics/pipeline/reviews`);
                const data = await res.json();
                setReviews(data.items || []);
                setLoading(false);
            } catch (e) {
                console.error("Error fetching human review cases:", e);
            }
        };

        fetchReviews();
        const interval = setInterval(fetchReviews, 10000);
        return () => clearInterval(interval);
    }, []);

    const handleAction = async (radicado, action) => {
        // Lógica para aprobar, rechazar o pedir ajuste a la IA
        console.log(`Acción ${action} ejecutada para ${radicado}`);
    };

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-100 pb-6">
                <div>
                    <h3 className="text-2xl font-black text-slate-900 flex items-center gap-3">
                        <Scale className="w-6 h-6 text-indigo-600" /> Bandeja de Revisión Humana
                    </h3>
                    <p className="text-slate-500 text-sm font-medium mt-1">Auditando casos con confianza inferior a 0.85 o riesgo legal alto.</p>
                </div>
                <div className="flex items-center gap-2">
                    <span className="px-3 py-1 rounded-full bg-rose-50 text-rose-600 text-[10px] font-black uppercase tracking-widest border border-rose-100">
                        {reviews.length} Casos Pendientes
                    </span>
                </div>
            </div>

            {/* List */}
            <div className="grid grid-cols-1 gap-4">
                {reviews.length === 0 ? (
                    <div className="py-20 bg-slate-50 rounded-[2rem] border-2 border-dashed border-slate-200 flex flex-col items-center justify-center text-slate-400">
                        <CheckCircle className="w-12 h-12 mb-4 opacity-20" />
                        <p className="font-bold uppercase tracking-widest text-xs">Sin casos para revisión manual</p>
                    </div>
                ) : (
                    reviews.map((item) => (
                        <div key={item.radicado} className="bg-white border border-slate-100 p-6 rounded-[2rem] hover:shadow-xl hover:shadow-slate-200/40 transition-all group">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-6">
                                    <div className="w-14 h-14 bg-indigo-50 rounded-2xl flex items-center justify-center text-indigo-600">
                                        <ShieldAlert className="w-7 h-7" />
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-3">
                                            <span className="text-xs font-mono font-black text-slate-400">{item.radicado}</span>
                                            <span className={`px-2 py-0.5 rounded-md text-[9px] font-black uppercase ${item.confidence < 0.6 ? 'bg-rose-100 text-rose-600' : 'bg-amber-100 text-amber-600'}`}>
                                                Confianza: {(item.confidence * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        <h4 className="text-base font-bold text-slate-800 mt-1">{item.asunto || "Solicitud de Capacitación"}</h4>
                                        <p className="text-xs text-slate-500 mt-1">Motivo: <span className="text-slate-700 italic">{item.reason || "Fallo umbral de seguridad"}</span></p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-4">
                                    <button 
                                        onClick={() => setSelectedTask(item)}
                                        className="px-6 py-3 bg-slate-900 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-indigo-600 transition-all flex items-center gap-2"
                                    >
                                        <Search className="w-3.5 h-3.5" /> Auditar Datos
                                    </button>
                                    <div className="flex gap-1">
                                        <button className="p-3 bg-emerald-50 text-emerald-600 rounded-xl hover:bg-emerald-500 hover:text-white transition-all">
                                            <CheckCircle className="w-4 h-4" />
                                        </button>
                                        <button className="p-3 bg-rose-50 text-rose-600 rounded-xl hover:bg-rose-500 hover:text-white transition-all">
                                            <XCircle className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Modal de Auditoría */}
            {selectedCase && (
                <div className="fixed inset-0 z-50 bg-slate-900/80 backdrop-blur-md flex items-center justify-center p-6 animate-in fade-in">
                    <div className="bg-white rounded-[3rem] shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col border border-white/20">
                        <div className="p-8 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                            <div>
                                <span className="text-[10px] font-black text-indigo-600 uppercase tracking-widest mb-1 block">Panel de Supervisión Técnica</span>
                                <h3 className="text-2xl font-black text-slate-900">{selectedCase.radicado}</h3>
                            </div>
                            <button onClick={() => setSelectedTask(null)} className="p-3 bg-white rounded-2xl hover:bg-slate-100 transition-all border border-slate-100 shadow-sm">
                                <XCircle className="w-5 h-5 text-slate-400" />
                            </button>
                        </div>

                        <div className="flex-1 overflow-y-auto p-12 grid grid-cols-1 lg:grid-cols-2 gap-12 custom-scrollbar">
                            <div className="space-y-10">
                                <section>
                                    <div className="flex items-center gap-2 text-indigo-600 mb-4">
                                        <Info className="w-4 h-4" />
                                        <h4 className="text-[10px] font-black uppercase tracking-widest">Alerta de Auditoría</h4>
                                    </div>
                                    <div className="p-6 bg-rose-50 border border-rose-100 rounded-3xl space-y-3">
                                        <p className="text-sm font-bold text-rose-900 flex items-center gap-2">
                                            <AlertCircle className="w-4 h-4" /> Motivo del Bloqueo:
                                        </p>
                                        <p className="text-sm text-rose-700 leading-relaxed font-medium">
                                            {selectedCase.reason || "La IA generó una respuesta que no coincide satisfactoriamente con la fundamentación legal inyectada."}
                                        </p>
                                    </div>
                                </section>

                                <section>
                                    <div className="flex items-center gap-2 text-slate-400 mb-4">
                                        <Scale className="w-4 h-4" />
                                        <h4 className="text-[10px] font-black uppercase tracking-widest">Hechos Detectados</h4>
                                    </div>
                                    <div className="text-sm text-slate-600 leading-relaxed bg-slate-50 p-6 rounded-3xl border border-slate-100">
                                        {selectedCase.hechos_extraidos || "El ciudadano solicita capacitación técnica para manipulación de alimentos en la JAC Calimio para octubre de 2025."}
                                    </div>
                                </section>
                            </div>

                            <div className="space-y-8">
                                <div className="p-8 bg-slate-900 rounded-[2.5rem] text-white shadow-2xl space-y-6 relative overflow-hidden">
                                    <div className="flex items-center justify-between relative z-10">
                                        <div className="flex items-center gap-2 text-emerald-400">
                                            <CheckCircle className="w-4 h-4" />
                                            <h4 className="text-[10px] font-black uppercase tracking-widest">Proyección a Corregir</h4>
                                        </div>
                                        <span className="px-3 py-1 bg-white/10 rounded-full text-[9px] font-black text-white/40 uppercase">Diamond V65.14</span>
                                    </div>
                                    
                                    <div className="bg-white/5 border border-white/10 p-6 rounded-2xl max-h-[300px] overflow-y-auto custom-scrollbar text-sm font-medium leading-relaxed text-indigo-100/80">
                                        {selectedCase.borrador_proyeccion || "Respuesta proyectada bloqueada por seguridad."}
                                    </div>

                                    <div className="grid grid-cols-2 gap-3 relative z-10">
                                        <button className="py-4 bg-emerald-500 hover:bg-emerald-600 text-slate-900 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all shadow-xl shadow-emerald-500/20">
                                            Aprobar y Generar
                                        </button>
                                        <button className="py-4 bg-white/10 hover:bg-white/20 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all">
                                            Regenerar con IA
                                        </button>
                                    </div>
                                    <div className="absolute bottom-0 right-0 w-64 h-64 bg-indigo-500/10 blur-[80px] -mb-32 -mr-32"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
