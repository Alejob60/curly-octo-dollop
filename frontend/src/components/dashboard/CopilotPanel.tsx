import React, { useState, useRef, useEffect } from 'react';
import { Bot, Send, User, Sparkles, X, ChevronRight, MessageSquare, Clock } from 'lucide-react';
import { dashboardApi } from '../../lib/api';
import { CaseTimeline } from './CaseTimeline';

interface Message {
  role: 'bot' | 'user';
  text: string;
}

interface CopilotPanelProps {
  sessionId: string;
  onClose: () => void;
}

export const CopilotPanel: React.FC<CopilotPanelProps> = ({ sessionId, onClose }) => {
  const [activeTab, setActiveTab] = useState<'chat' | 'timeline'>('chat');
  const [messages, setMessages] = useState<Message[]>([
    { role: 'bot', text: '¡Hola! Soy tu Copiloto Judicial. Puedo ayudarte a resumir este caso, explicar el score de confianza o verificar la normativa aplicada. ¿En qué puedo asistirte?' }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;

    const userMsg = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setIsTyping(true);

    try {
      const res = await dashboardApi.askCopilot(sessionId, userMsg);
      setMessages(prev => [...prev, { role: 'bot', text: res.response }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'bot', text: 'Lo siento, hubo un error al procesar tu consulta. Por favor, intenta de nuevo.' }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl w-[450px] animate-in slide-in-from-right duration-300">
      {/* Header */}
      <header className="px-6 pt-6 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30">
        <div className="flex justify-between items-start mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-lg">
              <Sparkles size={20} />
            </div>
            <div>
              <h2 className="text-sm font-black text-slate-900 dark:text-white uppercase tracking-tight">Copiloto IA</h2>
              <p className="text-[10px] font-bold text-indigo-500 uppercase tracking-widest">Asistente Contextual</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
            <X size={20} />
          </button>
        </div>

        {/* TABS switcher */}
        <div className="flex gap-4 border-b border-transparent">
          <button 
            onClick={() => setActiveTab('chat')}
            className={`pb-3 text-[10px] font-black uppercase tracking-widest border-b-2 transition-all ${
              activeTab === 'chat' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-400 hover:text-slate-600'
            }`}
          >
            <div className="flex items-center gap-2">
              <MessageSquare size={14} /> Chat IA
            </div>
          </button>
          <button 
            onClick={() => setActiveTab('timeline')}
            className={`pb-3 text-[10px] font-black uppercase tracking-widest border-b-2 transition-all ${
              activeTab === 'timeline' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-400 hover:text-slate-600'
            }`}
          >
            <div className="flex items-center gap-2">
              <Clock size={14} /> Trazabilidad
            </div>
          </button>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {activeTab === 'chat' ? (
          <>
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
              {messages.map((msg, i) => (
                <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 shadow-sm ${
                    msg.role === 'bot' ? 'bg-indigo-600 text-white' : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                  }`}>
                    {msg.role === 'bot' ? <Bot size={16} /> : <User size={16} />}
                  </div>
                  <div className={`max-w-[85%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                    msg.role === 'bot' 
                      ? 'bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-tl-none border border-slate-100 dark:border-slate-700' 
                      : 'bg-indigo-600 text-white rounded-tr-none'
                  }`}>
                    {msg.text}
                  </div>
                </div>
              ))}
              {isTyping && (
                <div className="flex gap-3 animate-pulse">
                  <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0">
                    <Bot size={16} className="text-white" />
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-800 px-4 py-3 rounded-2xl rounded-tl-none border border-slate-100 dark:border-slate-700">
                    <div className="flex gap-1">
                      <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"></span>
                      <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:0.2s]"></span>
                      <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:0.4s]"></span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Input */}
            <div className="p-6 border-t border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900">
              <div className="relative">
                <textarea
                  rows={1}
                  placeholder="Escribe una pregunta jurídica..."
                  className="w-full pl-4 pr-12 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all dark:text-white resize-none"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
                />
                <button 
                  onClick={handleSend}
                  disabled={!input.trim() || isTyping}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-all disabled:opacity-50"
                >
                  <Send size={18} />
                </button>
              </div>
              <p className="text-[10px] text-slate-400 mt-3 text-center uppercase font-bold tracking-widest">
                Sugerencia: "Resume los hechos de este caso"
              </p>
            </div>
          </>
        ) : (
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            <CaseTimeline radicado={sessionId} />
          </div>
        )}
      </div>
    </div>
  );
};
