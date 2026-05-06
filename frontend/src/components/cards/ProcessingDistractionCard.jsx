import React, { useState, useEffect } from 'react';
import { Bot, Sparkles, Cpu, ShieldCheck, Zap, Database, Scale, Clock } from 'lucide-react';

export const ProcessingDistractionCard = ({ status }) => {
  const [distractionIndex, setDistractionIndex] = useState(0);
  const [seconds, setSeconds] = useState(0);
  
  const distractions = [
    "El Alcalde dice que Cali es la sucursal del cielo, pero el Ledger es la sucursal de la seguridad.",
    "Dato curioso: Cali tiene más de 12 ríos, pero solo un sistema de radicación inalterable.",
    "¿Sabías que el Alcalde madruga a las 5 AM? Nosotros también para procesar tu expediente.",
    "Cifrando datos... más rápido que un bus del MIO en carril solo.",
    "Validando leyes... Sin chistes de caleños, solo puro derecho administrativo.",
    "El Alcalde Alejandro Eder está trabajando por Cali, y nosotros por tu PQRSD.",
    "Dato del día: La Torre de Cali mide 183 metros, casi tanto como nuestra base de datos legal.",
    "Procesando... más dulce que un cholado en la novena.",
    "Analizando marco legal... con la seriedad de una sesión del Concejo.",
    "Asegurando tu privacidad... como el Alcalde asegura el futuro de la ciudad."
  ];

  // Cronómetro interno de la card
  useEffect(() => {
    const timer = setInterval(() => {
      setSeconds(prev => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Rotación de mensajes
  useEffect(() => {
    const interval = setInterval(() => {
      setDistractionIndex((prev) => (prev + 1) % distractions.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (s) => {
    const m = Math.floor(s / 60);
    const rs = s % 60;
    return `${m}:${rs.toString().padStart(2, '0')}`;
  };

  const getStatusIcon = () => {
    if (status.includes("identidad")) return <Database className="w-4 h-4 text-indigo-400" />;
    if (status.includes("rehidratando")) return <ShieldCheck className="w-4 h-4 text-emerald-400" />;
    if (status.includes("auditando") || status.includes("IA")) return <Scale className="w-4 h-4 text-amber-400" />;
    if (status.includes("generando")) return <Cpu className="w-4 h-4 text-blue-400" />;
    return <Zap className="w-4 h-4 text-indigo-400 animate-pulse" />;
  };

  return (
    <div className="bg-[#0A2540] text-white border border-white/20 rounded-2xl p-6 shadow-2xl w-full animate-in zoom-in-95 duration-500 overflow-hidden relative">
      <div className="absolute top-0 right-0 p-4 opacity-10">
        <Cpu className="w-24 h-24 animate-spin-slow" />
      </div>
      
      <div className="relative z-10 space-y-6">
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/20 rounded-lg border border-indigo-400/30">
              <Sparkles className="w-5 h-5 text-indigo-300 animate-pulse" />
            </div>
            <div>
              <h3 className="text-xs font-black uppercase tracking-[0.2em] text-white leading-none text-left">Procesando Expediente</h3>
              <p className="text-[7px] font-bold text-indigo-300/60 uppercase tracking-widest mt-1 text-left">Seguridad Forense Orbital Prime</p>
            </div>
          </div>
          
          {/* 🔥 CRONÓMETRO INTEGRADO */}
          <div className="flex items-center gap-2 bg-white/5 px-3 py-1.5 rounded-full border border-white/10">
            <Clock className="w-3 h-3 text-indigo-400 animate-pulse" />
            <span className="text-[10px] font-black font-mono text-indigo-200">{formatTime(seconds)}</span>
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-white/5 rounded-xl p-5 border border-white/10 shadow-inner">
            <p className="text-[11px] font-medium text-indigo-50 color-indigo-100 leading-relaxed italic text-center min-h-[50px] flex items-center justify-center">
              "{distractions[distractionIndex]}"
            </p>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-2">
                {getStatusIcon()}
                <span className="text-[9px] font-black uppercase tracking-widest text-indigo-200">{status}</span>
              </div>
              <span className="text-[8px] font-bold text-indigo-400 animate-pulse tracking-[0.2em]">SISTEMA ACTIVO</span>
            </div>
            <div className="w-full bg-white/10 h-2 rounded-full overflow-hidden border border-white/5 p-[1px]">
                <div className="bg-indigo-500 h-full animate-progress-indefinite rounded-full shadow-[0_0_12px_rgba(99,102,241,1)]" />
            </div>
          </div>
        </div>

        <div className="pt-2 flex justify-center">
          <p className="text-[7px] text-indigo-300/40 font-bold text-center uppercase tracking-[0.3em] animate-pulse">
            Certificando integridad en el Ledger Municipal
          </p>
        </div>
      </div>
    </div>
  );
};
