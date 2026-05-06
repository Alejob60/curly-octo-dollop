import React from 'react';
import { ClipboardCheck, ShieldCheck, ChevronRight, User, MapPin, FileText, Zap } from 'lucide-react';

export const ConfirmationCard = ({ data, onConfirm }) => {
  const handleConfirm = () => {
    onConfirm({ confirmado: true });
  };

  return (
    <div className="bg-white border-2 border-indigo-500/20 rounded-2xl p-6 shadow-2xl w-full animate-in zoom-in-95 duration-500 text-slate-900 overflow-hidden relative">
      <div className="absolute top-0 right-0 p-4 opacity-5">
        <ClipboardCheck className="w-24 h-24 text-indigo-600" />
      </div>

      <div className="flex flex-col gap-6 relative z-10">
        <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
          <div className="p-2 bg-indigo-600 rounded-lg shadow-lg shadow-indigo-200">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 leading-none">Confirmación de Radicación</h3>
            <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest mt-1">Verifique su información antes del sello digital</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {/* SECCIÓN IDENTIDAD */}
          <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
            <div className="flex items-center gap-2 mb-2">
              <User className="w-3 h-3 text-indigo-500" />
              <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Identidad del Peticionario</p>
            </div>
            <p className="text-[11px] font-bold text-slate-800">{data.nombres} {data.apellidos}</p>
            <p className="text-[9px] text-slate-500 font-medium">{data.tipo_documento}: {data.documento}</p>
          </div>

          {/* SECCIÓN CONTACTO */}
          <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
            <div className="flex items-center gap-2 mb-2">
              <MapPin className="w-3 h-3 text-rose-500" />
              <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Ubicación y Notificación</p>
            </div>
            <p className="text-[10px] font-bold text-slate-800">{data.direccion}</p>
            <p className="text-[9px] text-slate-500 font-medium">{data.email} | {data.celular}</p>
          </div>

          {/* RESUMEN MAGISTRAL IA */}
          <div className="bg-indigo-50/30 rounded-xl p-4 border border-indigo-100 relative overflow-hidden">
            <div className="absolute top-2 right-2">
                <Zap className="w-3 h-3 text-amber-400 animate-pulse" />
            </div>
            <div className="flex items-center gap-2 mb-3">
              <FileText className="w-3 h-3 text-indigo-600" />
              <p className="text-[8px] font-black text-indigo-600 uppercase tracking-widest">Resumen Analítico del Caso</p>
            </div>
            <div className="text-[10px] font-medium text-slate-700 leading-relaxed italic">
              {data.resumen_confirmacion || "Su solicitud está siendo procesada bajo los términos de la Ley 1755 de 2015 para una respuesta de fondo efectiva."}
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <p className="text-[7px] text-slate-400 font-bold text-center uppercase tracking-widest px-4">
            Al confirmar, el sistema generará el expediente electrónico inalterable en el Ledger de la Alcaldía.
          </p>
          
          <div className="flex flex-col gap-2">
            <button 
                onClick={handleConfirm}
                className="w-full bg-slate-900 text-white font-black py-4 rounded-xl text-[10px] uppercase tracking-[0.2em] hover:bg-indigo-600 transition-all shadow-xl flex items-center justify-center gap-3 group"
            >
                Confirmar y Radicar Ahora
                <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>

            <button 
                onClick={() => onConfirm({ edit_mode: true })}
                className="w-full bg-white border-2 border-slate-100 text-slate-500 font-black py-3 rounded-xl text-[9px] uppercase tracking-[0.2em] hover:bg-slate-50 transition-all flex items-center justify-center gap-3"
            >
                Corregir Información
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
