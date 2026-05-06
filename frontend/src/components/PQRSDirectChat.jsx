import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Sparkles, ShieldAlert, FileText, Download, CheckCircle2, Clock, Folder, Zap } from 'lucide-react';
import { IdentityCard } from './cards/IdentityCard';
import { ContactCard } from './cards/ContactCard';
import { EvidenceAndLegalCard } from './cards/EvidenceAndLegalCard';
import { ConfirmationCard } from './cards/ConfirmationCard';
import { SuccessCard } from './cards/SuccessCard';
import { ProcessingDistractionCard } from './cards/ProcessingDistractionCard';

export const PQRSDirectChat = () => {
  // 🔥 PERSISTENCIA DE SESIÓN
  const [sessionId] = useState(() => {
    const saved = sessionStorage.getItem('orbital_session_id');
    if (saved) return saved;
    const newId = `session-${Math.random().toString(36).substr(2, 9)}`;
    sessionStorage.setItem('orbital_session_id', newId);
    return newId;
  });

  const [messages, setMessages] = useState(() => {
    const saved = sessionStorage.getItem(`orbital_msgs_${sessionId}`);
    return saved ? JSON.parse(saved) : [{
        role: 'assistant',
        content: "👋 ¡Hola! Soy el asistente virtual de PQRSD de la **Alcaldía de Santiago de Cali**. Escribe tu solicitud detallada en un solo mensaje."
    }];
  });

  const [userMessageCount, setUserMessageCount] = useState(() => {
    const saved = sessionStorage.getItem(`orbital_count_${sessionId}`);
    return saved ? parseInt(saved, 10) : 0;
  });

  const [input, setInput] = useState("");
  
  // 🔥 ESTADO DE MISIÓN CRÍTICA: Bloquea la UI para el Magistrado
  const [isProcessing, setIsProcessing] = useState(() => {
    // Si hay una card de procesamiento o terminada en el historial, recuperamos estado
    return messages.some(m => m.type === 'card' && (m.cardType === 'ProcessingCard' || m.cardType === 'SuccessCard')) ? false : false;
  });

  const [processingStatus, setProcessingStatus] = useState("Iniciando protocolos...");
  const scrollRef = useRef(null);
  const pollingRef = useRef(null);

  // Auto-scroll
  const forceScroll = () => {
    if (scrollRef.current) {
        scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }
  };

  useEffect(() => {
    forceScroll();
    const t = setTimeout(forceScroll, 300);
    return () => clearTimeout(t);
  }, [messages, isProcessing, processingStatus]);

  // Persistencia de mensajes
  useEffect(() => {
    sessionStorage.setItem(`orbital_msgs_${sessionId}`, JSON.stringify(messages));
    sessionStorage.setItem(`orbital_count_${sessionId}`, userMessageCount.toString());
  }, [messages, userMessageCount, sessionId]);

  // 🔥 POLLING DE PROGRESO (Resiliente a refrescos)
  useEffect(() => {
    if (isProcessing) {
      console.log("📡 [POLLING_ACTIVE] session:", sessionId);
      
      pollingRef.current = setInterval(async () => {
        try {
          const response = await fetch(`http://localhost:8000/api/v1/pqrs/progress/${sessionId}`);
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
            addSystemMessage(`Error crítico: ${data.message}`);
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

  const handleUpdateSlot = async (slots) => {
    // 🔥 TRIGGER DE FASE 4: Activación inmediata de la distracción
    if (slots.confirmado) {
        setIsProcessing(true);
        setProcessingStatus("Iniciando sellado digital...");
    }

    try {
      const response = await fetch('http://localhost:8000/api/v1/pqrs/update-slot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, slots })
      });
      const instruction = await response.json();
      
      // Si el backend ya mandó la card de procesamiento, aseguramos estado
      if (instruction.cardType === 'ProcessingCard') {
          setIsProcessing(true);
          setProcessingStatus(instruction.message || "Auditoría en curso...");
      } else {
          processBackendInstruction(instruction);
      }
    } catch (e) {
      setIsProcessing(false);
      addSystemMessage("Error de conexión.");
    }
  };

  const processBackendInstruction = (instruction) => {
    if (instruction.message) {
      setMessages(prev => [...prev, { role: 'assistant', content: instruction.message }]);
    }

    if (instruction.type === 'card') {
        setMessages(prev => [...prev, { 
          role: 'assistant', 
          type: 'card', 
          cardType: instruction.cardType, 
          data: instruction.data 
        }]);
    }
  };

  const renderFinalSuccess = (result) => {
    // Evitar duplicar SuccessCard
    if (messages.some(m => m.cardType === 'SuccessCard')) return;
    
    setMessages(prev => [...prev, { 
      role: 'assistant', 
      type: 'card', 
      cardType: 'SuccessCard', 
      data: result 
    }]);
  };

  const addSystemMessage = (text) => {
    setMessages(prev => [...prev, { role: 'system', content: text }]);
  };

  const onSend = () => {
    if (!input.trim() || isProcessing) return;
    const text = input;
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setInput("");
    const newCount = userMessageCount + 1;
    setUserMessageCount(newCount);
    if (newCount === 1) handleInitialAnalyze(text);
  };

  const handleInitialAnalyze = async (text) => {
    setIsProcessing(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/pqrs/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: text })
      });
      const instruction = await response.json();
      processBackendInstruction(instruction);
    } catch (e) {
      addSystemMessage("Error de red.");
    } finally {
      setIsProcessing(false);
    }
  };

  const renderMessage = (msg, i) => {
    if (msg.role === 'system') return (
      <div key={i} className="flex justify-center"><span className="bg-rose-50 text-rose-600 text-[8px] font-bold px-2 py-1 rounded-full uppercase flex items-center gap-1"><ShieldAlert className="w-2 h-2"/> {msg.content}</span></div>
    );

    return (
      <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in duration-300`}>
        <div className={`flex gap-3 max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
          <div className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center border ${msg.role === 'user' ? 'bg-white' : 'bg-[#0A2540] text-white shadow-lg'}`}>
            {msg.role === 'user' ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
          </div>
          <div className="space-y-2">
            {msg.content && (
              <div className={`px-4 py-2.5 rounded-2xl text-[12px] shadow-sm border ${
                  msg.role === 'user' ? 'bg-slate-800 text-white border-slate-700' : 'bg-white border-slate-200 text-slate-700'
              }`}>
                {msg.content}
              </div>
            )}
            {msg.type === 'card' && (
              <div className="w-full min-w-[280px]">
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
    );
  };

  return (
    <div className="flex flex-col h-full bg-[#FDFCF8] relative">
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
                <p className="text-[8px] text-slate-400 font-medium italic">No cierre esta ventana, estamos sellando su radicado...</p>
             </div>
           </div>
        </div>
      )}

      <header className="bg-[#0A2540] text-white p-4 flex items-center justify-between border-b border-white/10 shadow-xl z-10">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-500/20 p-2 rounded-lg border border-indigo-400/30"><Bot className="w-5 h-5 text-indigo-300" /></div>
          <div>
            <div className="flex items-center gap-2">
                <h1 className="text-xs font-black uppercase tracking-[0.2em] text-white">Orbital GovDoc</h1>
                <span className="bg-emerald-500 text-[6px] px-1.5 py-0.5 rounded-full font-black animate-pulse">DIAMOND_V64_STABLE</span>
            </div>
            <p className="text-[7px] font-bold text-indigo-300 uppercase tracking-widest opacity-80 text-left">Alcaldía de Santiago de Cali</p>
          </div>
        </div>
        
        <button 
            onClick={() => {
                sessionStorage.clear();
                localStorage.clear();
                window.location.reload();
            }}
            className="text-[7px] font-black uppercase tracking-widest text-indigo-300/40 hover:text-indigo-300 transition-colors border border-indigo-300/10 px-2 py-1 rounded"
        >
            Limpiar Sesión
        </button>
      </header>

      <main ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg, i) => renderMessage(msg, i))}
      </main>

      <footer className="p-6 bg-white border-t border-slate-100 shadow-2xl z-10">
        <div className="max-w-3xl mx-auto flex items-center gap-2 bg-slate-50 border border-slate-200 p-1.5 rounded-2xl shadow-inner focus-within:bg-white focus-within:border-indigo-400 transition-all">
          <input 
            className="flex-1 bg-transparent border-none px-4 text-sm font-medium outline-none text-slate-700" 
            placeholder={isProcessing ? "El sistema está trabajando..." : "Escribe tu PQRS aquí..."}
            value={input}
            disabled={isProcessing}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && onSend()}
          />
          <button 
            onClick={onSend}
            disabled={isProcessing}
            className="p-3 bg-slate-900 text-white rounded-xl hover:bg-indigo-600 active:scale-95 transition-all shadow-lg disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </footer>
    </div>
  );
};
