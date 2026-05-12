import React, { useState, useEffect } from 'react';
import { Activity, ShieldCheck, Database, Zap, AlertTriangle, ChevronRight, BarChart3, Clock, Scale } from 'lucide-react';

export const DiamondPipelineMonitor = () => {
    const [metrics, setMetrics] = useState({
        queue: { total_backlog: 0, pending: 0, processing: 0, completed: 0, failed: 0 },
        performance: { avg_confidence: 0, success_rate: 100, vertex_status: "HEALTHY" },
        system: { version: "V65.14", timestamp: Date.now() }
    });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
        const fetchMetrics = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/v1/metrics/pipeline`);
                const data = await res.json();
                if (data.queue) setMetrics(data);
                setLoading(false);
            } catch (e) {
                console.error("Error fetching pipeline metrics:", e);
            }
        };

        fetchMetrics();
        const interval = setInterval(fetchMetrics, 5000);
        return () => clearInterval(interval);
    }, []);

    const kpis = [
        { label: "Backlog Total", value: metrics.queue.total_backlog.toLocaleString(), icon: Database, color: "text-slate-900", bg: "bg-slate-50" },
        { label: "En Proceso", value: metrics.queue.processing, icon: Zap, color: "text-amber-500", bg: "bg-amber-50", animate: metrics.queue.processing > 0 },
        { label: "Confianza IA", value: `${(metrics.performance.avg_confidence * 100).toFixed(0)}%`, icon: ShieldCheck, color: "text-emerald-600", bg: "bg-emerald-50" },
        { label: "Fallas (DLQ)", value: metrics.queue.failed, icon: AlertTriangle, color: metrics.queue.failed > 0 ? "text-rose-600" : "text-slate-300", bg: "bg-rose-50" }
    ];

    return (
        <div className="bg-slate-900 rounded-[3rem] p-10 text-white shadow-2xl relative overflow-hidden border border-white/5">
            {/* Background Glow */}
            <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-600/20 blur-[100px] -mr-48 -mt-48"></div>
            
            <div className="relative z-10 space-y-12">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="space-y-2">
                        <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded bg-emerald-500 text-slate-900 text-[10px] font-black uppercase tracking-widest">Live Pipeline</span>
                            <span className="text-[10px] text-white/40 font-bold uppercase tracking-widest">Diamond Refactored V65.14</span>
                        </div>
                        <h3 className="text-3xl font-black tracking-tighter">Sala de Control: Migración 46k</h3>
                    </div>
                    <div className="flex flex-col items-end">
                        <div className={`flex items-center gap-2 px-4 py-2 rounded-2xl border ${metrics.performance.vertex_status === 'HEALTHY' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-rose-500/10 border-rose-500/30 text-rose-400'}`}>
                            <Activity className={`w-4 h-4 ${metrics.performance.vertex_status === 'HEALTHY' ? 'animate-pulse' : ''}`} />
                            <span className="text-xs font-black uppercase tracking-widest">Vertex AI: {metrics.performance.vertex_status}</span>
                        </div>
                    </div>
                </div>

                {/* KPI Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                    {kpis.map((kpi, i) => (
                        <div key={i} className="bg-white/5 border border-white/10 p-6 rounded-3xl hover:bg-white/10 transition-all group">
                            <div className={`p-3 rounded-xl w-fit ${kpi.bg} ${kpi.color} mb-4 group-hover:scale-110 transition-transform`}>
                                <kpi.icon className={`w-5 h-5 ${kpi.animate ? 'animate-spin-slow' : ''}`} />
                            </div>
                            <p className="text-[10px] font-bold text-white/40 uppercase tracking-widest">{kpi.label}</p>
                            <h4 className="text-2xl font-black mt-1">{kpi.value}</h4>
                        </div>
                    ))}
                </div>

                {/* Progress Visualizer */}
                <div className="space-y-6">
                    <div className="flex items-center justify-between text-xs font-bold uppercase tracking-widest">
                        <span className="text-white/60">Progreso de Migración Global</span>
                        <span className="text-emerald-400">{((metrics.queue.completed / (metrics.queue.total_backlog || 1)) * 100).toFixed(2)}%</span>
                    </div>
                    <div className="h-4 bg-white/5 rounded-full overflow-hidden p-1 border border-white/10">
                        <div 
                            className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-500 rounded-full transition-all duration-1000 shadow-[0_0_15px_rgba(16,185,129,0.5)]"
                            style={{ width: `${(metrics.queue.completed / (metrics.queue.total_backlog || 1)) * 100}%` }}
                        ></div>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-4 pt-4">
                        <div className="text-center p-4 bg-white/5 rounded-2xl border border-white/5">
                            <p className="text-[9px] text-white/30 font-bold uppercase">Completados</p>
                            <p className="text-lg font-black text-emerald-400">{metrics.queue.completed}</p>
                        </div>
                        <div className="text-center p-4 bg-white/5 rounded-2xl border border-white/5">
                            <p className="text-[9px] text-white/30 font-bold uppercase">En Cola</p>
                            <p className="text-lg font-black text-indigo-400">{metrics.queue.pending}</p>
                        </div>
                        <div className="text-center p-4 bg-white/5 rounded-2xl border border-white/5">
                            <p className="text-[9px] text-white/30 font-bold uppercase">Efectividad IA</p>
                            <p className="text-lg font-black text-purple-400">{metrics.performance.success_rate}%</p>
                        </div>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-4">
                    <button className="flex-1 py-4 bg-indigo-600 hover:bg-indigo-700 rounded-2xl font-black text-xs uppercase tracking-widest transition-all shadow-xl shadow-indigo-900/40 flex items-center justify-center gap-2">
                        <BarChart3 className="w-4 h-4" /> Ver Reporte de Auditoría
                    </button>
                    <button className="px-6 py-4 bg-white/10 hover:bg-white/20 rounded-2xl font-black text-xs uppercase tracking-widest transition-all flex items-center justify-center gap-2">
                        <Scale className="w-4 h-4" /> Human Review Queue
                        {metrics.queue.failed > 0 && <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>}
                    </button>
                </div>
            </div>
        </div>
    );
};
