import { useState, useRef } from "react";
import { 
  User, Mail, MapPin, FileText, Send, 
  UploadCloud, X, CheckCircle2, AlertCircle, 
  Loader2, ShieldCheck, Download, Search,
  ArrowRight, Building2, Smartphone, Share2, Sparkles
} from "lucide-react";
import { useI18n } from "../i18n";

export function FormalCitizenPortal() {
  const { t } = useI18n();
  const fileInputRef = useRef(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionResult, setIntegrationResult] = useState(null);
  const [error, setError] = useState(null);
  const [attachments, setAttachments] = useState([]);
  
  const [formData, setFormData] = useState({
    tipo_solicitante: "Persona Natural", tipo_documento: "CC", documento: "",
    nombres: "", primer_apellido: "", segundo_apellido: "",
    email: "", celular: "", departamento: "Valle del Cauca", municipio: "Cali",
    direccion: "", asunto: "", motivo: "", autorizacion_datos: false
  });

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    setAttachments(prev => [...prev, ...files.map(f => ({ file: f, id: Math.random().toString(36).substr(2, 9) }))]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.autorizacion_datos) { alert("Debe autorizar el tratamiento de datos personales."); return; }
    setIsSubmitting(true); setError(null);
    try {
      const audit_draft = {
        peticionario: { tipo_solicitante: formData.tipo_solicitante, tipo_documento: formData.tipo_documento, documento: formData.documento, nombres: formData.nombres, primer_apellido: formData.primer_apellido, segundo_apellido: formData.segundo_apellido },
        contacto: { departamento: formData.departamento, municipio: formData.municipio, direccion: formData.direccion, celular: formData.celular, email: formData.email },
        hechos: { asunto: formData.asunto, motivo: formData.motivo, dependencias_ids: ["4136"], dependencia_principal_nombre: "SECRETARÍA DE GOBIERNO" }
      };
      
      const response = await fetch(`${apiBaseUrl}/api/v1/pqrs/direct-submit`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audit_draft, session_id: `formal-${Date.now()}` })
      });
      
      const result = await response.json();
      if (result.status === "success") {
        // Aseguramos URLs absolutas
        result.artifacts = Object.fromEntries(
            Object.entries(result.artifacts).map(([k, v]) => [k, `${apiBaseUrl}${v}`])
        );
        setIntegrationResult(result);
      } else {
        throw new Error(result.message || "Fallo en el servidor");
      }
    } catch (err) { 
        setError(err.message); 
    } finally { 
        setIsSubmitting(false); 
    }
  };

  const labelCls = "text-[9px] font-black text-slate-400 uppercase tracking-wider mb-1 block";
  const inputCls = "w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-[11px] font-bold text-slate-700 outline-none focus:ring-1 focus:ring-indigo-500/30 transition-all placeholder:text-slate-300";

  if (submissionResult) {
    return (
      <div className="flex-1 bg-slate-50 p-4 flex items-center justify-center overflow-y-auto">
        <div className="max-w-md w-full bg-white rounded-3xl shadow-2xl p-8 text-center animate-in zoom-in-95 duration-500 border border-emerald-100 relative">
          <div className="absolute top-0 right-0 p-4 opacity-5"><ShieldCheck className="w-20 h-24 text-emerald-600" /></div>
          
          <div className="p-4 bg-emerald-500 rounded-full w-20 h-20 flex items-center justify-center mx-auto mb-6 shadow-xl shadow-emerald-200">
            <CheckCircle2 className="w-10 h-10 text-white" />
          </div>
          
          <h2 className="text-2xl font-black text-slate-900 mb-1 uppercase tracking-tight">Radicación Exitosa</h2>
          <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest mb-6">ID OFICIAL: {submissionResult.radicado_id}</p>
          
          <div className="space-y-3 w-full">
            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest text-left ml-1">Documentos Certificados:</p>
            
            <a href={submissionResult.artifacts.memorial_usuario} download target="_blank" rel="noreferrer" className="flex items-center justify-between bg-slate-900 text-white p-4 rounded-2xl hover:bg-indigo-600 transition-all group shadow-lg">
                <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-emerald-400" />
                    <span className="text-[11px] font-bold uppercase tracking-widest text-left">Descargar Memorial</span>
                </div>
                <Download className="w-4 h-4 group-hover:translate-y-0.5 transition-transform" />
            </a>

            <div className="grid grid-cols-2 gap-3">
                <a href={submissionResult.artifacts.oficio_traslado} download target="_blank" rel="noreferrer" className="flex items-center justify-center gap-2 bg-slate-50 border border-slate-200 text-slate-700 p-3 rounded-2xl hover:bg-slate-100 transition-all text-[9px] font-black uppercase tracking-widest">
                  <Share2 className="w-4 h-4 text-indigo-500" /> Traslado
                </a>
                <a href={submissionResult.artifacts.borrador_proyeccion} download target="_blank" rel="noreferrer" className="flex items-center justify-center gap-2 bg-slate-50 border border-slate-200 text-slate-700 p-3 rounded-2xl hover:bg-slate-100 transition-all text-[9px] font-black uppercase tracking-widest">
                  <Sparkles className="w-4 h-4 text-amber-500" /> Borrador
                </a>
            </div>

            <button onClick={() => setIntegrationResult(null)} className="w-full text-slate-400 font-bold uppercase tracking-widest text-[9px] py-4 flex items-center justify-center gap-1 hover:text-indigo-600 transition-colors">
              Radicar otra solicitud <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-white p-4 lg:p-10 scrollbar-hide">
      <div className="max-w-5xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
        <header className="flex items-center justify-between mb-8 border-b border-slate-100 pb-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-[#0A2540] rounded-2xl shadow-indigo-100 shadow-2xl rotate-3"><Building2 className="w-6 h-6 text-white" /></div>
            <div>
              <h1 className="text-xl font-black text-slate-900 tracking-tighter flex items-center gap-2 uppercase italic">
                Portal Ciudadano <span className="text-indigo-600 not-italic opacity-30">Prime</span>
              </h1>
              <p className="text-[11px] text-slate-400 font-bold uppercase tracking-[0.3em]">Radicación Directa y Forense</p>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-4 bg-slate-50 px-4 py-2 rounded-2xl border border-slate-100">
            <div className="text-right"><p className="text-[8px] font-black text-slate-300 uppercase tracking-tighter leading-none">Security Level</p><p className="text-[10px] font-black text-indigo-600 tracking-tighter uppercase">GCP-WORM ACTIVE</p></div>
            <ShieldCheck className="w-6 h-6 text-indigo-600" />
          </div>
        </header>

        <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-7 space-y-6">
            <div className="bg-[#F8FAFC] rounded-3xl border border-slate-200/60 p-6 relative overflow-hidden shadow-sm">
                <div className="absolute top-0 right-0 p-6 opacity-[0.02] rotate-12"><User className="w-24 h-24" /></div>
                <h2 className="text-[11px] font-black text-indigo-900/40 uppercase tracking-[0.3em] mb-6 flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-indigo-500 shadow-lg shadow-indigo-200"></div> Identidad Legal
                </h2>
                <div className="grid grid-cols-6 gap-4">
                    <div className="col-span-2">
                        <label className={labelCls}>Tipo Solicitante</label>
                        <select name="tipo_solicitante" value={formData.tipo_solicitante} onChange={handleChange} className={inputCls}>
                            <option>Persona Natural</option><option>Persona Juridica</option>
                        </select>
                    </div>
                    <div className="col-span-1">
                        <label className={labelCls}>Tipo Doc</label>
                        <select name="tipo_documento" value={formData.tipo_documento} onChange={handleChange} className={inputCls}>
                            <option>CC</option><option>NIT</option><option>CE</option>
                        </select>
                    </div>
                    <div className="col-span-3">
                        <label className={labelCls}>Número de Documento</label>
                        <input type="text" name="documento" required value={formData.documento} onChange={handleChange} className={inputCls} placeholder="Sin puntos ni guiones" />
                    </div>
                    <div className="col-span-6">
                        <label className={labelCls}>Nombre(s) Completo(s)</label>
                        <input type="text" name="nombres" required value={formData.nombres} onChange={handleChange} className={inputCls} placeholder="Tal como aparece en el documento" />
                    </div>
                    <div className="col-span-3">
                        <label className={labelCls}>Primer Apellido</label>
                        <input type="text" name="primer_apellido" required value={formData.primer_apellido} onChange={handleChange} className={inputCls} />
                    </div>
                    <div className="col-span-3">
                        <label className={labelCls}>Segundo Apellido</label>
                        <input type="text" name="segundo_apellido" value={formData.segundo_apellido} onChange={handleChange} className={inputCls} />
                    </div>
                </div>
            </div>

            <div className="bg-[#FFFBFB] rounded-3xl border border-rose-100 p-6 relative overflow-hidden shadow-sm">
                <div className="absolute top-0 right-0 p-6 opacity-[0.02] -rotate-12"><Smartphone className="w-24 h-24" /></div>
                <h2 className="text-[11px] font-black text-rose-900/40 uppercase tracking-[0.3em] mb-6 flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-rose-500 shadow-lg shadow-rose-200"></div> Contacto y Ubicación
                </h2>
                <div className="grid grid-cols-6 gap-4">
                    <div className="col-span-3">
                        <label className={labelCls}>Correo Electrónico</label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-2 w-4 h-4 text-slate-300" />
                            <input type="email" name="email" required value={formData.email} onChange={handleChange} className={`${inputCls} pl-9`} placeholder="notificaciones@correo.com" />
                        </div>
                    </div>
                    <div className="col-span-3">
                        <label className={labelCls}>Celular de Contacto</label>
                        <input type="tel" name="celular" required value={formData.celular} onChange={handleChange} className={inputCls} placeholder="31X XXX XXXX" />
                    </div>
                    <div className="col-span-6">
                        <label className={labelCls}>Dirección en Cali</label>
                        <div className="relative">
                            <MapPin className="absolute left-3 top-2 w-4 h-4 text-slate-300" />
                            <input type="text" name="direccion" required value={formData.direccion} onChange={handleChange} className={`${inputCls} pl-9`} placeholder="Barrio, Calle, Número..." />
                        </div>
                    </div>
                </div>
            </div>
          </div>

          <div className="lg:col-span-5 space-y-6">
            <div className="bg-white rounded-3xl border border-slate-200 p-6 h-full flex flex-col shadow-xl">
                <h2 className="text-[11px] font-black text-emerald-900/40 uppercase tracking-[0.3em] mb-6 flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-lg shadow-emerald-200"></div> Hechos de la Solicitud
                </h2>
                <div className="space-y-4 flex-1">
                    <div>
                        <label className={labelCls}>Asunto o Título</label>
                        <input type="text" name="asunto" required value={formData.asunto} onChange={handleChange} className={inputCls} placeholder="Ej: Rectificación Catastral..." />
                    </div>
                    <div className="flex-1 flex flex-col min-h-[150px]">
                        <label className={labelCls}>Descripción Detallada (Hechos)</label>
                        <textarea name="motivo" required value={formData.motivo} onChange={handleChange} className={`${inputCls} flex-1 resize-none leading-relaxed p-4 bg-white`} placeholder="Relate su solicitud de forma clara..."></textarea>
                    </div>

                    <div className="grid grid-cols-1 gap-4 mt-4">
                        <div onClick={() => fileInputRef.current.click()} className="group border-2 border-dashed border-slate-200 rounded-2xl p-6 text-center cursor-pointer hover:border-indigo-400 hover:bg-indigo-50/50 transition-all flex flex-col items-center justify-center bg-slate-50/50">
                            <input type="file" ref={fileInputRef} className="hidden" multiple onChange={handleFileChange} />
                            <UploadCloud className="w-8 h-8 text-slate-300 mb-2 group-hover:text-indigo-500 transition-colors" />
                            <span className="text-[9px] font-black uppercase tracking-widest text-slate-400 group-hover:text-indigo-600">Adjuntar Evidencia</span>
                        </div>
                        {attachments.length > 0 && (
                          <div className="bg-indigo-50/30 border border-indigo-100 rounded-2xl p-4 space-y-2">
                             {attachments.map(att => (
                                <div key={att.id} className="flex items-center justify-between text-[10px] font-bold text-slate-600 bg-white p-2 rounded-lg border border-indigo-50 shadow-sm">
                                    <span className="truncate max-w-[150px]">{att.file.name}</span>
                                    <button type="button" onClick={() => setAttachments(prev => prev.filter(a => a.id !== att.id))} className="text-slate-300 hover:text-rose-500"><X className="w-3.5 h-3.5" /></button>
                                </div>
                             ))}
                          </div>
                        )}
                    </div>
                </div>

                <div className="mt-8 pt-6 border-t border-slate-100">
                    <div className="flex items-start gap-3 mb-6 group cursor-pointer" onClick={() => setFormData(prev => ({ ...prev, autorizacion_datos: !prev.autorizacion_datos }))}>
                        <div className={`w-5 h-5 mt-0.5 rounded-lg border-2 transition-all flex items-center justify-center shrink-0 ${formData.autorizacion_datos ? 'bg-indigo-600 border-indigo-600 shadow-lg shadow-indigo-200' : 'bg-white border-slate-200'}`}>
                            {formData.autorizacion_datos && <CheckCircle2 className="w-3.5 h-3.5 text-white" />}
                        </div>
                        <div>
                            <p className="text-[10px] font-black text-slate-800 uppercase tracking-tight">Habeas Data & Notificación</p>
                            <p className="text-[9px] text-slate-400 font-bold leading-tight uppercase tracking-tighter mt-0.5">Autorizo tratamiento según Ley 1581 de 2012</p>
                        </div>
                    </div>

                    <button type="submit" disabled={isSubmitting} className={`w-full py-4 rounded-2xl font-black uppercase tracking-[0.3em] shadow-2xl transition-all flex items-center justify-center gap-3 text-xs ${isSubmitting ? 'bg-slate-100 text-slate-300 cursor-not-allowed shadow-none' : 'bg-[#0A2540] text-white hover:bg-indigo-600 active:scale-95 shadow-indigo-100 hover:shadow-indigo-500/20'}`}>
                        {isSubmitting ? <Loader2 className="w-5 h-5 animate-spin" /> : <><Send className="w-4 h-4" /> Finalizar Radicación</>}
                    </button>
                </div>
            </div>
          </div>
        </form>

        <footer className="mt-12 text-center py-6 border-t border-slate-50">
            <p className="text-[9px] text-slate-300 font-black uppercase tracking-[0.5em] flex items-center justify-center gap-3">
                <ShieldCheck className="w-4 h-4 opacity-50" /> Orbital Prime · Cali Digital Ecosystem · 2026
            </p>
        </footer>
      </div>
    </div>
  );
}
