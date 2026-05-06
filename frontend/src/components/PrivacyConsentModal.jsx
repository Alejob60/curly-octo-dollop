import React, { useState } from 'react';
import { ShieldCheck, Building2, ChevronRight, Lock, Loader2 } from 'lucide-react';

export const PrivacyConsentModal = ({ onAccept }) => {
  const [accepted, setAccepted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleIngresar = async () => {
    if (!accepted || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await onAccept();
    } catch (error) {
      console.error("Error in onAccept:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/80 backdrop-blur-md animate-in fade-in duration-300">
      <div className="bg-white rounded-[2.5rem] shadow-2xl max-w-lg w-full overflow-hidden border border-slate-200 animate-in zoom-in-95 duration-500">
        
        {/* ENCABEZADO INSTITUCIONAL */}
        <div className="bg-[#0A2540] p-8 text-white relative">
          <div className="absolute top-0 right-0 p-8 opacity-10"><ShieldCheck className="w-32 h-32" /></div>
          <div className="relative z-10">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-white/10 rounded-xl backdrop-blur-md"><Building2 className="w-5 h-5 text-indigo-300" /></div>
              <h2 className="text-xs font-black uppercase tracking-[0.2em] text-indigo-200">Tratamiento de Datos</h2>
            </div>
            <h1 className="text-2xl font-black tracking-tighter leading-tight uppercase">Consentimiento <br/> Ciudadano Soberano</h1>
          </div>
        </div>

        {/* CUERPO LEGAL */}
        <div className="p-8 space-y-6">
          <div className="bg-slate-50 border border-slate-100 rounded-3xl p-6 max-h-48 overflow-y-auto custom-scrollbar">
            <p className="text-[11px] text-slate-600 leading-relaxed font-medium">
              Conforme a la **Ley 1581 de 2012** y el **Decreto 1377 de 2013**, la Alcaldía de Santiago de Cali informa que los datos personales recolectados a través de **Orbital Prime** serán tratados bajo estrictos protocolos de seguridad y confidencialidad. 
              <br/><br/>
              Sus datos serán utilizados exclusivamente para:
              <br/>
              1. Identificación y radicación de solicitudes PQRSD.
              <br/>
              2. Notificación oficial del estado de sus trámites.
              <br/>
              3. Generación de actos administrativos con validez jurídica.
              <br/><br/>
              El sistema utiliza un **Escudo de Privacidad Forense** que anonimiza sus datos antes de ser procesados por Inteligencia Artificial. La información rehidratada solo reside en el búnker de datos de la Alcaldía.
            </p>
          </div>

          <label className="flex items-start gap-4 p-4 rounded-2xl border-2 border-slate-100 hover:border-indigo-100 transition-all cursor-pointer group">
            <input 
              type="checkbox" 
              checked={accepted} 
              onChange={(e) => setAccepted(e.target.checked)} 
              className="mt-1 w-5 h-5 accent-indigo-600 cursor-pointer"
            />
            <div>
              <p className="text-[11px] font-black text-slate-800 uppercase leading-none">Acepto la Política de Privacidad</p>
              <p className="text-[9px] text-slate-400 mt-1 font-bold">Autorizo el tratamiento de mis datos personales según la Ley 1581.</p>
            </div>
          </label>

          <button 
            disabled={!accepted || isSubmitting}
            onClick={handleIngresar}
            className={`w-full py-5 rounded-2xl flex items-center justify-center gap-3 text-xs font-black uppercase tracking-[0.2em] transition-all shadow-xl ${accepted && !isSubmitting ? 'bg-slate-900 text-white hover:bg-indigo-600 active:scale-95 shadow-indigo-900/40' : 'bg-slate-100 text-slate-300 cursor-not-allowed shadow-none'}`}
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Lock className="w-4 h-4" />
            )}
            {isSubmitting ? 'Procesando...' : 'Ingresar al Portal'}
            {!isSubmitting && <ChevronRight className="w-4 h-4" />}
          </button>
        </div>

        {/* FOOTER */}
        <div className="bg-slate-50 py-4 px-8 border-t border-slate-100 text-center">
          <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">
            Sello de Garantía Habeas Data · Cali Digital 2026
          </p>
        </div>
      </div>
    </div>
  );
};

