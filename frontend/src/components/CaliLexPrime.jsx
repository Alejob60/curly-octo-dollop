import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Send, Bot, User, Sparkles, ShieldCheck, Terminal, FileText, Download, Clock, Zap, Building2, Phone, Globe } from 'lucide-react';
import { IdentityCard } from './cards/IdentityCard';
import { ContactCard } from './cards/ContactCard';
import { EvidenceAndLegalCard } from './cards/EvidenceAndLegalCard';
import { ConfirmationCard } from './cards/ConfirmationCard';
import { SuccessCard } from './cards/SuccessCard';
import { PrivacyConsentModal } from './PrivacyConsentModal';
import { ProcessingDistractionCard } from './cards/ProcessingDistractionCard';

const API_BASE = "http://localhost:8000/api/v1/pqrs";

export const CaliLexPrime = () => {
  // 🔥 PERSISTENCIA DE SESIÓN
  const sessionId = useMemo(() => {
      const stored = localStorage.getItem("active_pqrs_session");
      if (stored) return stored;
      const newId = `session-${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem("active_pqrs_session", newId);
      return newId;
  }, []);

  const [messages, setMessages] = useState(() => {
    const saved = sessionStorage.getItem(`orbital_msgs_${sessionId}`);
    return saved ? JSON.parse(saved) : [];
  });

  const [input, setInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState("Iniciando...");
  const [hasConsent, setHasConsent] = useState(sessionStorage.getItem('habeas_data_accepted') === 'true');
  const scrollRef = useRef(null);
  const pollingRef = useRef(null);
  const [statusLogs, setStatusLogs] = useState([]);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isProcessing, processingStatus]);

  // Persistencia de mensajes
  useEffect(() => {
    sessionStorage.setItem(`orbital_msgs_${sessionId}`, JSON.stringify(messages));
  }, [messages, sessionId]);

  // Bienvenida inicial
  useEffect(() => {
    if (hasConsent && messages.length === 0) {
      const greeting = {
        role: 'assistant',
        content: "👋 ¡Hola! Soy el asistente virtual de PQRSD de la **Alcaldía de Santiago de Cali**. He verificado su autorización de datos. Por favor, **escribe en un solo mensaje su solicitud detallada**."
      };
      setMessages([greeting]);
      addLog("SISTEMA DIAMOND V64.2 STABLE", "ia");
    }
  }, [hasConsent]);

  // 🔥 POLLING DE PROGRESO (Fix de Bloqueo Final)
  useEffect(() => {
    if (isProcessing) {
      console.log("📡 [POLLING_ACTIVE] session:", sessionId);
      
      pollingRef.current = setInterval(async () => {
        try {
          const response = await fetch(`${API_BASE}/progress/${sessionId}`);
          const data = await response.json();
          console.log("📊 [POLLING_DATA]", data);
          
          if (data.status === 'complete') {
            console.log("✅ [POLLING_SUCCESS]");
            clearInterval(pollingRef.current);
            setIsProcessing(false);
            if (data.data) renderFinalSuccess(data.data);
          } else if (data.status === 'error') {
            clearInterval(pollingRef.current);
            setIsProcessing(false);
            addLog(`ERROR: ${data.message}`, "error");
          } else if (data.progress !== undefined) {
            setProcessingStatus(data.message || "Procesando documentos...");
          }
        } catch (e) {
          console.warn("📡 [POLLING_RETRY]");
        }
      }, 2000);
    }
    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, [isProcessing, sessionId]);

  const addLog = (text, type = "process") => {
    const uniqueId = `${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
    setStatusLogs(prev => [...prev, { id: uniqueId, text, type, time: new Date().toLocaleTimeString() }]);
  };

  const handleAcceptConsent = async () => {
    try {
      const response = await fetch(`${API_BASE}/register-consent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, consent_type: "habeas_data" })
      });
      const result = await response.json();
      if (result.status === 'success') {
        sessionStorage.setItem('habeas_data_accepted', 'true');
        setHasConsent(true);
      }
    } catch (e) {
      alert("⚠️ Error de conexión con el servidor.");
    }
  };

  const handleInitialAnalyze = async (text) => {
    setIsProcessing(true);
    setProcessingStatus("Analizando solicitud...");
    addLog("IA: Iniciando Análisis Forense...", "ia");
    try {
      const response = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: text })
      });
      const instruction = await response.json();
      processInstruction(instruction);
    } catch (e) {
      addLog("ERROR: Fallo de conexión.", "error");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleUpdateSlot = async (slots) => {
    // 🔥 TRIGGER FASE 4: Sello Digital
    if (slots.confirmado) {
        setIsProcessing(true);
        setProcessingStatus("Iniciando protocolos de sellado...");
        addLog("SELLADO DIGITAL INICIADO", "shield");
    }

    try {
      const response = await fetch(`${API_BASE}/update-slot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, slots })
      });
      const instruction = await response.json();
      
      if (instruction.cardType === 'ProcessingCard') {
          setIsProcessing(true);
          setProcessingStatus(instruction.message || "Generando memoriales...");
      } else {
          processInstruction(instruction);
      }
    } catch (e) {
      setIsProcessing(false);
      addLog("ERROR: Fallo al actualizar.", "error");
    }
  };

  const processInstruction = (ins) => {
    if (ins.message) setMessages(prev => [...prev, { role: 'assistant', content: ins.message }]);
    if (ins.type === 'card') {
      setMessages(prev => [...prev, { role: 'assistant', type: 'card', cardType: ins.cardType, data: ins.data }]);
    }
  };

  const renderFinalSuccess = (result) => {
    addLog("EXPEDIENTE SELLADO CON ÉXITO", "success");
    setMessages(prev => [...prev, { 
      role: 'assistant', 
      type: 'card', 
      cardType: 'SuccessCard', 
      data: result 
    }]);
  };

  const onSend = (e) => {
    if (e) e.preventDefault();
    if (!input.trim() || isProcessing) return;
    const text = input;
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setInput("");
    if (messages.filter(m => m.role === 'user').length === 0) handleInitialAnalyze(text);
  };

  return (
    <div className="flex h-screen w-full bg-[#F1F5F9] overflow-hidden font-sans">
      
      {!hasConsent && <PrivacyConsentModal onAccept={handleAcceptConsent} />}

      {/* OVERLAY DE DISTRACCIÓN: Máxima prioridad visual */}
      {isProcessing && (
        <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-50 flex items-center justify-center p-6 animate-in fade-in duration-500">
           <div className="w-full max-w-sm">
             <ProcessingDistractionCard status={processingStatus} />
             <div className="mt-4 flex flex-col items-center gap-2">
                <div className="flex items-center gap-2 text-indigo-600 font-bold text-[10px] uppercase tracking-widest">
                    <Zap className="w-3 h-3 animate-pulse" />
                    Auditoría IA en curso
                </div>
                <p className="text-[8px] text-slate-400 font-medium italic text-center">No cierre esta ventana, el Magistrado está sellando su radicado...</p>
             </div>
           </div>
        </div>
      )}

      <aside className="w-64 bg-[#0A2540] text-white p-4 flex-none flex-col border-r border-white/10 hidden lg:flex h-full overflow-hidden">
        <div className="flex items-center gap-2 mb-6 border-b border-white/5 pb-4 shrink-0">
          <Terminal className="w-4 h-4 text-indigo-400" />
          <h2 className="text-[10px] font-black uppercase tracking-widest text-indigo-200">Forensic Status Log</h2>
        </div>
        <div className="flex-1 space-y-3 overflow-y-auto pr-2 custom-scrollbar">
          {statusLogs.map(log => (
            <div key={log.id} className="animate-in slide-in-from-left-2 duration-300">
              <div className="flex justify-between items-center mb-1">
                <span className={`text-[7px] font-black uppercase px-1.5 py-0.5 rounded ${
                  log.type === 'shield' ? 'bg-indigo-500/20 text-indigo-300' :
                  log.type === 'ia' ? 'bg-purple-500/20 text-purple-300' :
                  log.type === 'error' ? 'bg-rose-500/20 text-rose-300' :
                  log.type === 'success' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-white/10 text-slate-400'
                }`}>{log.type}</span>
                <span className="text-[6px] text-white/30 font-mono">{log.time}</span>
              </div>
              <p className="text-[9px] font-medium text-slate-300 leading-tight border-l border-white/10 pl-2">{log.text}</p>
            </div>
          ))}
        </div>
      </aside>

      <div className="flex-1 flex flex-col h-screen overflow-hidden relative">
        <header className="flex-none bg-white border-b border-slate-200 p-4 flex items-center justify-between shadow-sm z-10">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[#0A2540] rounded-xl shadow-lg shadow-indigo-900/20"><Bot className="w-5 h-5 text-white" /></div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xs font-black uppercase tracking-[0.2em] text-slate-800 leading-none">CaliLex Prime</h1>
                <span className="bg-emerald-500 text-white text-[6px] px-1.5 py-0.5 rounded-full font-black animate-pulse">DIAMOND_V64_STABLE</span>
              </div>
              <p className="text-[7px] font-bold text-indigo-600 uppercase tracking-widest mt-1">Motor Judicial Unificado</p>
            </div>
          </div>
          
          <button 
                onClick={() => { sessionStorage.clear(); localStorage.clear(); window.location.reload(); }}
                className="text-[7px] font-black uppercase tracking-widest text-slate-400 hover:text-indigo-600 transition-colors border border-slate-100 px-2 py-1 rounded-lg"
            >
                Resetear Chat
          </button>
        </header>

        <div className="flex-1 flex flex-col overflow-hidden">
          <main ref={scrollRef} className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6 custom-scrollbar bg-[#FDFCF8]/50">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} w-full`}>
                <div className={`flex gap-2 md:gap-3 max-w-[95%] md:max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-7 h-7 md:w-8 md:h-8 rounded-lg shrink-0 flex items-center justify-center border ${msg.role === 'user' ? 'bg-white' : 'bg-[#0A2540] text-white shadow-md'}`}>
                    {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>
                  <div className="space-y-3 min-w-0 overflow-hidden">
                    {msg.content && (
                      <div className={`px-4 py-2.5 md:px-5 md:py-3.5 rounded-2xl text-[12px] md:text-[13px] shadow-sm border leading-relaxed break-words ${
                        msg.role === 'user' ? 'bg-slate-800 text-white border-slate-700' : 'bg-white border-slate-200 text-slate-700'
                      }`}>
                        {msg.content}
                      </div>
                    )}
                    {msg.type === 'card' && (
                      <div className="w-full min-w-0 max-w-full">
                        {msg.cardType === 'IdentityCard' && <IdentityCard data={msg.data} onConfirm={handleUpdateSlot} />}
                        {msg.cardType === 'ContactCard' && <ContactCard data={msg.data} onConfirm={handleUpdateSlot} />}
                        {msg.cardType === 'EvidenceAndLegalCard' && <EvidenceAndLegalCard data={msg.data} onConfirm={handleUpdateSlot} isProcessing={isProcessing} />}
                        {msg.cardType === 'ConfirmationCard' && <ConfirmationCard data={msg.data} onConfirm={handleUpdateSlot} />}
                        {msg.cardType === 'SuccessCard' && <SuccessCard data={msg.data} />}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div className="h-4 shrink-0"></div>
          </main>

          <footer className="flex-none bg-white border-t border-slate-100 shadow-[0_-10px_25px_-5px_rgba(0,0,0,0.05)] z-10">
            <div className="p-3 md:p-6 pb-2">
                <form onSubmit={onSend} className="max-w-4xl mx-auto flex items-end gap-2 md:gap-3">
                    <textarea 
                        className="flex-1 min-w-0 bg-slate-50 border border-slate-200 p-3 md:p-4 text-xs md:text-sm font-medium outline-none text-slate-700 placeholder:text-slate-400 rounded-2xl shadow-inner focus:bg-white focus:border-indigo-400 transition-all resize-none max-h-32 min-h-[52px]" 
                        rows="1"
                        placeholder={isProcessing ? "El sistema está trabajando..." : "Escribe tu solicitud PQRSD aquí..."}
                        value={input}
                        disabled={isProcessing}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if(e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                onSend();
                            }
                        }}
                    />
                    <button type="submit" disabled={isProcessing || !input.trim()} className="flex-none w-12 h-[52px] bg-[#0A2540] text-white rounded-2xl hover:bg-indigo-600 active:scale-95 transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center shrink-0">
                        <Send className="w-5 h-5" />
                    </button>
                </form>
            </div>
            <div className="bg-slate-50 py-3 px-4 border-t border-slate-100">
                <div className="max-w-4xl mx-auto flex flex-wrap items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <Building2 className="w-4 h-4 text-slate-400" />
                        <p className="text-[8px] font-bold text-slate-500 uppercase tracking-widest">Centro Administrativo Municipal (CAM) - Cali, Valle del Cauca</p>
                    </div>
                </div>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
};
