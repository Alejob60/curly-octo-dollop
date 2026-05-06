import { useState, useRef, useEffect, useMemo } from "react";
import { Download, Send, Bot, User, Paperclip, X, Terminal, CheckCircle2, Sparkles, ShieldCheck, MapPinned, Gavel, ChevronRight, UploadCloud, Cpu, Scale, ShieldAlert, Clock, ClipboardCheck } from "lucide-react";
import { useI18n } from "../i18n";
import { useChatSocket } from "../hooks/useChatSocket";
import { IdentityCard } from "./cards/IdentityCard";
import { ContactCard } from "./cards/ContactCard";
import { EvidenceAndLegalCard } from "./cards/EvidenceAndLegalCard";
import { ConfirmationCard } from "./cards/ConfirmationCard";
import { SuccessCard } from "./cards/SuccessCard";
import { ProcessingStatusCard } from "./ProcessingStatusCard";

// UX-4.2: Banner de Contexto Persistente
function ContextBanner({ phase, caseName, radicado }) {
  const phases = ["IDENTIDAD", "UBICACIÓN", "ANÁLISIS", "EVIDENCIA", "FIRMA"];
  const currentIdx = ["fase_1_identidad", "fase_2_ubicacion", "fase_3_analisis", "fase_4_evidencia", "fase_5_generacion"].indexOf(phase);

  return (
    <div className="bg-[#0A2540] border-b border-white/10 px-6 py-2.5 flex items-center justify-between text-white animate-in slide-in-from-top duration-500 relative z-20 shadow-lg">
      <div className="flex items-center gap-4">
        <div className="flex flex-col">
            <span className="text-[7px] font-black text-indigo-400 uppercase tracking-widest">Estado del Expediente</span>
            <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold text-white uppercase">{caseName || "Trámite General"}</span>
                {radicado && <span className="bg-emerald-500/20 text-emerald-400 text-[8px] px-2 py-0.5 rounded-full border border-emerald-500/30 font-black">REF: {radicado}</span>}
            </div>
        </div>
      </div>
      <div className="flex items-center gap-6">
          <div className="hidden md:flex gap-1">
              {phases.map((p, i) => (
                  <div key={p} className="flex items-center gap-1">
                      <div className={`h-1 w-8 rounded-full transition-all duration-700 ${i <= currentIdx ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-white/10'}`} />
                  </div>
              ))}
          </div>
          <div className="flex items-center gap-2 border-l border-white/10 pl-4">
              <Clock className="w-3 h-3 text-indigo-300" />
              <span className="text-[9px] font-bold text-indigo-200">SLA: 15 DÍAS (LEY 1755)</span>
          </div>
      </div>
    </div>
  );
}

// UX-4.1: Smart Identity Form (No pide datos ya validados)
function IdentityFormUI({ onSubmit, existingData = {} }) {
  const [formData, setFormData] = useState({ 
      tipo_solicitante: 'Persona Natural', 
      tipo_documento: 'CC', 
      documento: existingData.documento || '', 
      nombres: existingData.nombres || '', 
      primer_apellido: '', 
      segundo_apellido: '' 
  });

  const handleSubmit = (e) => { 
    e.preventDefault(); 
    const summary = `BLOQUE 1 COMPLETADO: Identificación: CC ${formData.documento}. Peticionario: ${formData.nombres} ${formData.primer_apellido}.`; 
    onSubmit(summary); 
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 mt-2 shadow-sm w-full animate-in slide-in-from-bottom-2 duration-500 text-slate-900">
      <div className="flex items-center gap-2 mb-3">
        <div className="p-1 bg-indigo-600 rounded shadow-sm"><Scale className="w-3 h-3 text-white" /></div>
        <p className="text-[8px] font-black uppercase tracking-widest text-slate-400">Paso 1: Validación de Identidad</p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
                <label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Número de Cédula</label>
                <div className="relative">
                  <input type="text" value={formData.documento} required onChange={(e) => setFormData({...formData, documento: e.target.value})} className={`w-full bg-slate-50 border border-slate-200 rounded-lg p-1.5 text-[10px] font-bold outline-none focus:border-indigo-500`} />
                  {existingData.found_in_db && <ShieldCheck className="absolute right-2 top-2 w-3 h-3 text-emerald-500" />}
                </div>
            </div>
            <div className="space-y-1">
                <label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Nombre Completo</label>
                <input type="text" value={formData.nombres} required onChange={(e) => setFormData({...formData, nombres: e.target.value})} className="w-full bg-slate-50 border border-slate-200 rounded-lg p-1.5 text-[10px] font-bold outline-none focus:border-indigo-500" />
            </div>
        </div>
        <button type="submit" className="w-full bg-slate-900 text-white font-bold py-2.5 rounded-lg text-[8px] uppercase tracking-[0.2em] hover:bg-indigo-600 transition-all shadow-sm">Confirmar Identidad</button>
        {existingData.found_in_db && <div className="flex items-center gap-2 text-emerald-600 text-[8px] font-black uppercase mt-1"><CheckCircle2 className="w-3 h-3" /> Ciudadano Verificado en Base de Datos</div>}
      </form>
    </div>
  );
}

// Bloque 2 Smart
function ContactFormUI({ onSubmit, existingData = {} }) {
    const [formData, setFormData] = useState({ direccion: existingData.direccion || '', celular: existingData.celular || '', email: existingData.email || '' });
    
    const handleSubmit = (e) => {
      e.preventDefault();
      const summary = `BLOQUE 2 COMPLETADO: Dirección: ${formData.direccion}. Contacto: Cel ${formData.celular}, Email ${formData.email}.`;
      onSubmit(summary);
    };

    return (
      <div className="bg-white border border-slate-200 rounded-xl p-4 mt-2 shadow-sm w-full animate-in slide-in-from-bottom-2 duration-500 text-slate-900">
        <div className="flex items-center gap-2 mb-3">
            <div className="p-1 bg-rose-600 rounded shadow-sm"><MapPinned className="w-3 h-3 text-white" /></div>
            <p className="text-[8px] font-black uppercase tracking-widest text-slate-400">Paso 2: Ubicación de Notificación</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-1">
            <label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Dirección en Cali</label>
            <input type="text" value={formData.direccion} required onChange={(e) => setFormData({...formData, direccion: e.target.value})} className="w-full bg-slate-50 border border-slate-200 rounded-lg p-1.5 text-[10px] font-bold outline-none focus:border-rose-500" />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1"><label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Celular</label><input type="tel" required value={formData.celular} onChange={(e) => setFormData({...formData, celular: e.target.value})} className="w-full bg-slate-50 border border-slate-200 rounded-lg p-1.5 text-[10px] font-bold outline-none" /></div>
            <div className="space-y-1"><label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Email</label><input type="email" required value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} className="w-full bg-slate-50 border border-slate-200 rounded-lg p-1.5 text-[10px] font-bold outline-none" /></div>
          </div>
          <button type="submit" className="w-full font-bold py-2.5 rounded-lg text-[8px] uppercase tracking-[0.2em] transition-all shadow-sm bg-rose-600 text-white hover:bg-rose-700">Guardar Ubicación</button>
        </form>
      </div>
    );
}

// Bloque 4 Evidence
function EvidenceFormUI({ onSubmit }) {
    const [files, setFiles] = useState([]);
    const inputRef = useRef(null);
    return (
      <div className="bg-slate-900 border border-indigo-500/30 rounded-xl p-5 mt-2 shadow-2xl w-full animate-in zoom-in-95 duration-500">
        <div className="flex items-center gap-2 mb-4">
            <div className="p-1 bg-indigo-500 rounded shadow-lg shadow-indigo-500/20"><UploadCloud className="w-4 h-4 text-white" /></div>
            <div>
                <p className="text-[9px] font-black uppercase tracking-widest text-indigo-300">Paso 4: Acervo Probatorio</p>
                <p className="text-[7px] text-indigo-400/60 font-bold uppercase tracking-widest">Documentos requeridos para el grounding jurídico</p>
            </div>
        </div>
        <div className="space-y-4">
            <div onClick={() => inputRef.current?.click()} className="border-2 border-dashed border-indigo-500/20 rounded-xl p-8 flex flex-col items-center justify-center gap-3 hover:bg-indigo-500/5 transition-all cursor-pointer group">
                <UploadCloud className="w-8 h-8 text-indigo-400/40 group-hover:text-indigo-400 transition-all" />
                <span className="text-[9px] font-black text-indigo-300 uppercase tracking-widest text-center">Subir archivos de evidencia</span>
                <input type="file" ref={inputRef} className="hidden" multiple onChange={(e) => setFiles([...files, ...Array.from(e.target.files)])} />
            </div>
            {files.length > 0 && (
                <div className="space-y-1.5">
                    {files.map((f, i) => (
                        <div key={i} className="flex items-center justify-between bg-white/5 p-2 rounded-lg border border-white/5">
                            <span className="text-[9px] font-bold text-indigo-100 truncate">{f.name}</span>
                            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                        </div>
                    ))}
                </div>
            )}
            <button onClick={() => onSubmit("BLOQUE 4 COMPLETADO", files)} className="w-full bg-indigo-600 text-white font-black py-3 rounded-lg text-[9px] uppercase tracking-[0.2em] shadow-lg hover:bg-indigo-500">Radicar Expediente Blindado</button>
        </div>
      </div>
    );
}

export function CaliLexAdvisor({ role }) {
  const sessionId = useMemo(() => {
      const stored = localStorage.getItem("active_pqrs_session");
      if (stored) return stored;
      const newId = `session-${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem("active_pqrs_session", newId);
      return newId;
  }, []);

  const { messages: socketMessages, isTyping: socketTyping } = useChatSocket(sessionId);
  const [localMessages, setLocalMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState("analyzing");
  const [sessionState, setSessionState] = useState({ phase: "fase_1_identidad", caseName: "", radicado: "", data: {} });
  const [logs, setLogs] = useState([{ id: "init", text: "SISTEMA DETERMINÍSTICO V36.2 ACTIVO", type: "system", time: new Date().toLocaleTimeString() }]);

  useEffect(() => {
    if (localMessages.length === 0 && !isProcessing) {
        handleSend(""); 
    }
  }, []);

  const addLog = (text, type = "process") => {
    const id = `${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
    setLogs(prev => [...prev, { id, text, type, time: new Date().toLocaleTimeString() }]);
  };

  const handleUpdateSlot = async (slots) => {
      // 🛡️ PARACAÍDAS V60.1: No permitir avance si hay campos críticos vacíos
      if (slots.documento === "" || slots.email === "") {
          addLog("ADVERTENCIA: Campos obligatorios incompletos.", "error");
          return;
      }

      if (slots.confirmado) {
          handleFinalize();
          return;
      }

      const blockName = slots.autorizacion_datos ? "BLOQUE 3" : slots.email ? "BLOQUE 2" : "BLOQUE 1";
      await handleSend(`${blockName} COMPLETADO: ${JSON.stringify(slots)}`);
  };

  const handleFinalize = async () => {
    setIsProcessing(true);
    setProcessingStage("auditing");
    addLog("AUDITORÍA JURÍDICA IA EN PROCESO...", "ia");
    
    try {
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/pqrs/finalize`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId })
        });
        const result = await response.json();

        if (result.status === "success") {
            setProcessingStage("finalizing");
            addLog("EXPEDIENTE SELLADO EXITOSAMENTE.", "success");
            result.artifacts = Object.fromEntries(Object.entries(result.artifacts).map(([k,v]) => [k, `http://localhost:8000${v}`]));
            setLocalMessages(prev => [...prev, { 
                role: "assistant", 
                type: "card",
                cardType: "SuccessCard",
                data: result,
                timestamp: new Date().toLocaleTimeString() 
            }]);
        } else if (result.status === "warning") {
            addLog("COMPLEJIDAD DETECTADA: ESCALANDO...", "shield");
            setProcessingStage("escalated");
            setLocalMessages(prev => [...prev, { 
                role: "assistant", 
                content: `📑 **Expediente Recibido para Revisión Especial**\n\n${result.message}\n\n**Radicado Temporal:** \`${result.radicado_id}\``,
                timestamp: new Date().toLocaleTimeString() 
            }]);
        }
    } catch (e) {
        addLog(`ERROR: ${e.message}`, "error");
    } finally {
        setIsProcessing(false);
    }
  };

  const handleSend = async (explicitInput = null, specialFiles = []) => {
    const textToSend = (explicitInput || input).trim();
    if (!textToSend && localMessages.length > 0) return;
    setInput("");
    if (textToSend) setLocalMessages(prev => [...prev, { role: "user", content: textToSend, timestamp: new Date().toLocaleTimeString() }]);
    
    setIsProcessing(true);
    setProcessingStage("analyzing");
    
    try {
        const formData = new FormData();
        formData.append("issue", textToSend || "Hola");
        formData.append("session_id", sessionId);
        specialFiles.forEach(f => formData.append("files", f));

        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/multimodal/process-multimodal`, { method: "POST", body: formData });
        const result = await response.json();

        if (result.status === "inquiry" || result.status === "pending_signature") {
            setSessionState({
                phase: result.phase || sessionState.phase,
                caseName: result.data_consolidada?.hechos?.asunto || sessionState.caseName,
                radicado: result.radicado_id || sessionState.radicado,
                data: result.data_consolidada
            });
            
            const newMsg = { 
                role: "assistant", 
                content: result.respuesta_chat, 
                bloque: result.bloque, 
                phase: result.phase,
                data_consolidada: result.data_consolidada,
                timestamp: new Date().toLocaleTimeString() 
            };
            
            if (result.status === "pending_signature") {
                newMsg.type = "card";
                newMsg.cardType = "ConfirmationCard";
                newMsg.data = result.data_consolidada;
            }

            setLocalMessages(prev => [...prev, newMsg]);
            addLog(`FASE ACTUALIZADA: ${result.status.toUpperCase()}`, "ia");
        }
    } catch (e) { addLog(`ERROR: ${e.message}`, "error"); } finally { setIsProcessing(false); }
  };

  const renderAction = (msg) => {
      if (msg.bloque === 1) return <IdentityFormUI existingData={msg.data_consolidada?.peticionario} onSubmit={(summary) => handleSend(summary)} />;
      if (msg.bloque === 2) return <ContactFormUI existingData={msg.data_consolidada?.contacto} onSubmit={(summary) => handleSend(summary)} />;
      if (msg.bloque === 4 || msg.phase === "fase_3_analisis") return <EvidenceFormUI onSubmit={(summary, files) => handleSend(summary, files)} />;
      if (msg.type === "card") {
          if (msg.cardType === "ConfirmationCard") return <ConfirmationCard data={msg.data} onConfirm={handleUpdateSlot} />;
          if (msg.cardType === "SuccessCard") return <SuccessCard data={msg.data} />;
      }
      if (msg.pdf) return (
          <a href={`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}${msg.pdf}`} target="_blank" rel="noreferrer" className="mt-3 flex items-center gap-2 bg-emerald-50 text-emerald-700 px-4 py-3 rounded-xl border border-emerald-100 hover:bg-emerald-100 transition-all group">
              <Download className="w-4 h-4 group-hover:bounce" />
              <div className="flex flex-col"><span className="text-[10px] font-black uppercase tracking-widest">Descargar Expediente</span><span className="text-[8px] font-bold opacity-60">Documento Oficial con Grounding Jurídico</span></div>
          </a>
      );
      return null;
  };

  const scrollRef = useRef(null);
  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }); }, [localMessages, socketTyping, isProcessing]);

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#FDFCF8]">
      <ContextBanner phase={sessionState.phase} caseName={sessionState.caseName} radicado={sessionState.radicado} />
      <div className="flex-1 flex overflow-hidden">
        <aside className="flex-[0.25] bg-[#0A2540] flex flex-col border-r border-white/5 relative overflow-hidden hidden md:flex">
          <div className="h-12 border-b border-white/5 px-4 flex items-center justify-between"><div className="flex items-center gap-2"><Terminal className="w-3.5 h-3.5 text-indigo-400" /><span className="text-[10px] font-black uppercase tracking-widest text-indigo-300">Audit Node V36.2</span></div></div>
          <div className="flex-1 overflow-y-auto p-6 font-mono text-[10px] space-y-4 custom-scrollbar">
            {logs.map(log => (
              <div key={log.id} className={`pl-2 border-l border-white/10 animate-in slide-in-from-left-2 duration-300`}>
                  <div className="text-[7px] opacity-40 mb-1">{log.time}</div>
                  <div className={`${log.type === 'success' ? 'text-emerald-400' : log.type === 'error' ? 'text-rose-400' : 'text-indigo-200/60'}`}>{log.text}</div>
              </div>
            ))}
          </div>
        </aside>
        <main className="flex-1 flex flex-col relative">
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6 custom-scrollbar">
            {[...socketMessages, ...localMessages].map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-in fade-in duration-500`}>
                <div className={`flex gap-3 max-w-[95%] md:max-w-[85%] ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                  <div className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center border ${msg.role === 'user' ? 'bg-white' : 'bg-[#0A2540] text-white shadow-lg'}`}>{msg.role === "user" ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}</div>
                  <div className="space-y-1">
                    <div className={`px-5 py-3 rounded-2xl text-[13px] shadow-sm border ${msg.role === "user" ? "bg-slate-800 text-white" : "bg-white border-slate-200 text-slate-700"}`}>
                      <div className="font-medium whitespace-pre-wrap">{msg.content}</div>
                      {renderAction(msg)}
                    </div>
                    <p className="text-[7px] text-slate-300 font-bold uppercase tracking-widest px-2">{msg.timestamp}</p>
                  </div>
                </div>
              </div>
            ))}
            {isProcessing && (
                <div className="w-full flex justify-start">
                    <ProcessingStatusCard stage={processingStage} />
                </div>
            )}
          </div>
          <div className="p-6">
            <div className="max-w-2xl mx-auto flex items-center gap-2 bg-white border border-slate-200 p-2 rounded-2xl shadow-xl focus-within:border-indigo-400 transition-all">
                <input className="flex-1 bg-transparent border-none px-4 text-sm font-medium outline-none" placeholder="Escriba su consulta jurídica..." value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSend()} />
                <button onClick={() => handleSend()} className="p-3 bg-slate-900 text-white rounded-xl hover:bg-indigo-600 transition-all shadow-lg"><Send className="w-4 h-4" /></button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
