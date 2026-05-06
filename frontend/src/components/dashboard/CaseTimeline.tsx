import React, { useEffect, useState } from 'react';
import { 
  FileText, Shield, MapPin, CheckCircle, 
  Clock, HardDrive, Key, AlertTriangle, ChevronDown, ChevronUp,
  RefreshCw, User, ShieldCheck
} from 'lucide-react';
import { dashboardApi } from '../../lib/api';

interface TimelineEvent {
  type: 'FORENSIC' | 'STATE_CHANGE';
  action: string;
  timestamp: string;
  details?: any;
  tx_id?: string;
  integrity_hash?: string;
  official?: string;
  comment?: string;
}

interface CaseTimelineProps {
  radicado: string;
}

export const CaseTimeline: React.FC<CaseTimelineProps> = ({ radicado }) => {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedEvent, setExpandedEvent] = useState<number | null>(null);

  useEffect(() => {
    const fetchTimeline = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/dashboard/cases/${radicado}/timeline`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        setEvents(data.events || []);
      } catch (error) {
        console.error("Error fetching timeline:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTimeline();
  }, [radicado]);

  const getIcon = (action: string) => {
    const a = action.toUpperCase();
    if (a.includes('INITIAL')) return <FileText size={16} className="text-blue-500" />;
    if (a.includes('PII') || a.includes('ANONYMIZED')) return <Shield size={16} className="text-purple-500" />;
    if (a.includes('ROUTING')) return <MapPin size={16} className="text-amber-500" />;
    if (a.includes('SIGNED') || a.includes('KMS')) return <Key size={16} className="text-emerald-500" />;
    if (a.includes('TRANSITION')) return <RefreshCw size={16} className="text-slate-500" />;
    return <CheckCircle size={16} className="text-slate-400" />;
  };

  if (isLoading) {
    return (
      <div className="p-12 flex flex-col items-center justify-center space-y-4">
        <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Reconstruyendo Línea de Tiempo Forense...</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-8">
        <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-lg">
          <Clock size={20} />
        </div>
        <div>
          <h2 className="text-sm font-black text-slate-900 dark:text-white uppercase tracking-tight">Trazabilidad E2E</h2>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Auditoría Forense Inmutable</p>
        </div>
      </div>

      <div className="relative space-y-6">
        {/* Línea vertical central */}
        <div className="absolute left-[15px] top-2 bottom-2 w-0.5 bg-slate-100 dark:bg-slate-800"></div>

        {events.length === 0 ? (
          <div className="pl-10 py-4 italic text-slate-400 text-xs">No hay eventos registrados para este radicado.</div>
        ) : (
          events.map((event, index) => (
            <div key={index} className="relative pl-10">
              {/* Punto en la línea */}
              <div className="absolute left-0 top-1 w-8 h-8 rounded-full bg-white dark:bg-slate-900 border-2 border-slate-100 dark:border-slate-800 flex items-center justify-center z-10 shadow-sm">
                {getIcon(event.action)}
              </div>

              <div className={`p-4 rounded-xl border transition-all ${
                expandedEvent === index ? 'bg-slate-50 dark:bg-slate-800/50 border-indigo-200 dark:border-indigo-900' : 'bg-white dark:bg-slate-900 border-slate-100 dark:border-slate-800'
              }`}>
                <div 
                  className="flex justify-between items-start cursor-pointer"
                  onClick={() => setExpandedEvent(expandedEvent === index ? null : index)}
                >
                  <div>
                    <span className="text-[9px] font-black text-indigo-500 uppercase tracking-widest mb-1 block">
                      {new Date(event.timestamp).toLocaleString()}
                    </span>
                    <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-tight">
                      {event.action.replace(/_/g, ' ')}
                    </h3>
                  </div>
                  <button className="text-slate-400">
                    {expandedEvent === index ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                </div>

                {expandedEvent === index && (
                  <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 animate-in fade-in slide-in-from-top-2 duration-200">
                    <div className="grid grid-cols-1 gap-3">
                      {event.type === 'FORENSIC' && (
                        <>
                          <div className="flex items-center gap-2">
                            <HardDrive size={12} className="text-slate-400" />
                            <span className="text-[10px] font-bold text-slate-500 uppercase">TX ID:</span>
                            <span className="text-[10px] font-mono text-slate-700 dark:text-slate-300 break-all">{event.tx_id}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Shield size={12} className="text-slate-400" />
                            <span className="text-[10px] font-bold text-slate-500 uppercase">Integrity Hash:</span>
                            <span className="text-[10px] font-mono text-slate-700 dark:text-slate-300">{event.integrity_hash}</span>
                          </div>
                        </>
                      )}
                      {event.official && (
                        <div className="flex items-center gap-2">
                          <User size={12} className="text-slate-400" />
                          <span className="text-[10px] font-bold text-slate-500 uppercase">Funcionario:</span>
                          <span className="text-[10px] text-slate-700 dark:text-slate-300">{event.official}</span>
                        </div>
                      )}
                      {event.details && (
                        <div className="mt-2 p-3 bg-slate-100 dark:bg-slate-800 rounded-lg overflow-x-auto">
                          <pre className="text-[9px] text-slate-600 dark:text-slate-400 font-mono">
                            {JSON.stringify(event.details, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-8 p-4 bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-800/50 rounded-xl flex items-start gap-3">
        <ShieldCheck className="text-emerald-500 shrink-0 mt-0.5" size={16} />
        <p className="text-[10px] text-emerald-700 dark:text-emerald-400 leading-relaxed font-medium">
          Esta línea de tiempo está vinculada a un Ledger Inmutable en GCP KMS. 
          Cualquier alteración en los registros invalidará el hash de integridad global del expediente.
        </p>
      </div>
    </div>
  );
};
