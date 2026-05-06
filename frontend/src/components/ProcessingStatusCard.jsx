import React, { useState, useEffect } from 'react';
import { ShieldCheck, Cpu, Database, Binary, FileCheck, Loader2, Sparkles, Scale, Zap } from 'lucide-react';

const TECHNICAL_STATUSES = [
  { text: "Iniciando protocolos de seguridad Habeas Data...", icon: <ShieldCheck className="w-4 h-4" /> },
  { text: "Estableciendo conexión con la Bóveda Digital Inmutable...", icon: <Database className="w-4 h-4" /> },
  { text: "Generando firma criptográfica para el radicado...", icon: <Binary className="w-4 h-4" /> },
  { text: "Consolidando fundamentos jurídicos (CPACA / Ley 1755)...", icon: <Cpu className="w-4 h-4" /> },
  { text: "Sincronizando con el Ledger Forense de GCP...", icon: <FileCheck className="w-4 h-4" /> },
  { text: "Rehidratando identidad legal en el expediente...", icon: <ShieldCheck className="w-4 h-4" /> },
  { text: "Sellando documentos con hash de integridad SHA-256...", icon: <Binary className="w-4 h-4" /> },
  { text: "Finalizando radicación oficial y registro Orfeo...", icon: <FileCheck className="w-4 h-4" /> }
];

const DISTRACTIONS = [
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

export const ProcessingStatusCard = ({ stage }) => {
  const [statusIndex, setStatusIndex] = useState(0);
  const [distractionIndex, setDistractionIndex] = useState(0);

  useEffect(() => {
    const statusInterval = setInterval(() => {
      setStatusIndex(prev => (prev + 1) % TECHNICAL_STATUSES.length);
    }, 4500);
    
    const distractionInterval = setInterval(() => {
      setDistractionIndex(prev => (prev + 1) % DISTRACTIONS.length);
    }, 3500);

    return () => {
        clearInterval(statusInterval);
        clearInterval(distractionInterval);
    };
  }, []);

  return (
    <div className="w-full max-w-sm mx-auto my-4 animate-in fade-in zoom-in duration-700">
      <div className="bg-[#0A2540] text-white rounded-3xl p-6 shadow-2xl border border-indigo-500/20 relative overflow-hidden">
        
        {/* Fondo decorativo tecnológico */}
        <div className="absolute top-0 right-0 p-4 opacity-10 rotate-12">
            <Cpu className="w-24 h-24 animate-spin-slow" />
        </div>
        
        <div className="relative z-10 space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-indigo-500/20 rounded-lg">
                <Sparkles className="w-3.5 h-3.5 text-indigo-300 animate-pulse" />
              </div>
              <span className="text-[9px] font-black uppercase tracking-[0.2em] text-indigo-300">Orbital Prime Forensics</span>
            </div>
            <div className="flex items-center gap-1.5">
                <div className="w-1 h-1 bg-emerald-500 rounded-full animate-ping" />
                <span className="text-[8px] font-mono text-indigo-400/60 uppercase">SECURE_CHANNEL_ACTIVE</span>
            </div>
          </div>

          <div className="space-y-4">
            {/* Distracción del Alcalde/Ciudad */}
            <div className="bg-white/5 rounded-2xl p-4 border border-white/5 min-h-[60px] flex items-center justify-center text-center animate-in fade-in duration-500" key={`dist-${distractionIndex}`}>
                <p className="text-[10px] font-medium text-indigo-100 leading-relaxed italic">
                    "{DISTRACTIONS[distractionIndex]}"
                </p>
            </div>

            {/* Status Técnico Real */}
            <div className="flex items-center gap-3 px-1 transition-all" key={`stat-${statusIndex}`}>
                <div className="text-indigo-400 animate-pulse">
                    {TECHNICAL_STATUSES[statusIndex].icon}
                </div>
                <div className="flex flex-col">
                    <p className="text-[11px] font-black text-white leading-none uppercase tracking-wider">
                        {TECHNICAL_STATUSES[statusIndex].text}
                    </p>
                    <p className="text-[7px] text-indigo-400 font-bold mt-1 uppercase tracking-widest">Verificando integridad...</p>
                </div>
            </div>

            {/* Barra de Progreso */}
            <div className="space-y-1.5">
                <div className="flex justify-between text-[7px] font-black uppercase tracking-widest text-slate-500 px-1">
                    <span>Procesamiento Forense</span>
                    <span>{Math.round(((statusIndex + 1) / TECHNICAL_STATUSES.length) * 100)}%</span>
                </div>
                <div className="h-1.5 bg-white/5 rounded-full overflow-hidden p-[1px]">
                    <div 
                        className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500 transition-all duration-1000 ease-in-out rounded-full shadow-[0_0_10px_rgba(99,102,241,0.5)]"
                        style={{ width: `${((statusIndex + 1) / TECHNICAL_STATUSES.length) * 100}%` }}
                    />
                </div>
            </div>
          </div>

          <div className="pt-2 flex items-center justify-between">
             <div className="flex items-center gap-2">
                <ShieldCheck className="w-3 h-3 text-emerald-500" />
                <p className="text-[8px] font-bold text-slate-400 uppercase tracking-tighter">
                    GCP-WORM INMUTABLE
                </p>
             </div>
             <p className="text-[7px] font-mono text-indigo-400/40">CALI_V60.0.1</p>
          </div>
        </div>
      </div>
    </div>
  );
};
