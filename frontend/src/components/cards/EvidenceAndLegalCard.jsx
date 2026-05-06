import React, { useState, useRef } from 'react';
import { UploadCloud, CheckCircle2, ShieldCheck, FileText, ChevronRight, Loader2 } from 'lucide-react';

export const EvidenceAndLegalCard = ({ data, onConfirm, isProcessing }) => {
  const [files, setFiles] = useState([]);
  const [authorized, setAuthorized] = useState(false);
  const fileInputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!authorized) {
      return;
    }
    // 🔧 FIX 4: Payload limpio (PR #01)
    onConfirm({ 
        autorizacion_datos: true,
        confirmed: true, // Clave estándar frontend
        confirmado: "true" // Clave estándar backend (redundancia segura)
    });
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-lg w-full animate-in zoom-in-95 duration-500 text-slate-900 overflow-hidden">
      <div className="flex items-center gap-2 mb-4 border-b border-slate-50 pb-3">
        <div className="p-1 bg-indigo-600 rounded shadow-sm">
          <UploadCloud className="w-4 h-4 text-white" />
        </div>
        <div>
          <p className="text-[9px] font-black uppercase tracking-widest text-slate-400">Paso 3: Evidencia y Cierre</p>
          <p className="text-[7px] text-indigo-600 font-bold uppercase tracking-widest opacity-60">Validación Jurídica y Probatoria</p>
        </div>
      </div>

      <div className="space-y-5">
        {/* Resumen del Asunto (Solo Lectura) */}
        <div className="bg-slate-50 border border-slate-100 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1.5">
            <FileText className="w-3 h-3 text-indigo-600" />
            <span className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Resumen del Asunto</span>
          </div>
          <p className="text-[10px] font-medium text-slate-600 leading-relaxed italic">
            "{data.asunto || 'Trámite general detectado por IA.'}"
          </p>
        </div>

        {/* Upload Section */}
        <div 
          onClick={() => !isProcessing && fileInputRef.current?.click()}
          className={`border-2 border-dashed border-slate-200 rounded-xl p-6 flex flex-col items-center justify-center gap-2 transition-all group ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'hover:bg-slate-50 cursor-pointer'}`}
        >
          <UploadCloud className={`w-8 h-8 text-slate-300 ${!isProcessing && 'group-hover:text-indigo-600'} transition-all`} />
          <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Subir Evidencia (PDF/JPG)</span>
          <input 
            type="file" 
            ref={fileInputRef} 
            className="hidden" 
            multiple 
            disabled={isProcessing}
            onChange={(e) => setFiles([...files, ...Array.from(e.target.files)])} 
          />
        </div>

        {files.length > 0 && (
          <div className="space-y-1.5">
            {files.map((f, i) => (
              <div key={i} className="flex items-center justify-between bg-slate-50 p-2 rounded-lg border border-slate-100">
                <span className="text-[9px] font-bold text-slate-600 truncate max-w-[200px]">{f.name}</span>
                <CheckCircle2 className="w-3 h-3 text-emerald-500" />
              </div>
            ))}
          </div>
        )}

        {/* Autorización Legal */}
        <div className="flex items-start gap-3 bg-indigo-50 p-3 rounded-lg border border-indigo-100">
          <input 
            type="checkbox" 
            id="legal_auth"
            checked={authorized}
            onChange={(e) => setAuthorized(e.target.checked)}
            disabled={isProcessing}
            className="mt-1 accent-indigo-600"
          />
          <label htmlFor="legal_auth" className="text-[8px] font-medium text-slate-500 leading-snug">
            Acepto la política de tratamiento de datos personales y autorizo la notificación a mi correo electrónico según la <span className="text-slate-800 font-bold underline cursor-pointer">Ley 1581 de 2012</span>.
          </label>
        </div>

        <button 
          onClick={handleSubmit}
          disabled={isProcessing || !authorized}
          className={`w-full font-black py-4 rounded-lg text-[10px] uppercase tracking-[0.2em] shadow-md transition-all flex items-center justify-center gap-2 group
            ${isProcessing 
              ? 'bg-slate-400 cursor-not-allowed' 
              : 'bg-slate-900 text-white hover:bg-indigo-600 active:scale-95'
            }`}
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Procesando Expediente...
            </>
          ) : (
            <>
              Validar Datos y Continuar
              <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </>
          )}
        </button>
      </div>
    </div>
  );
};
