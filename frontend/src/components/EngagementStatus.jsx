import React, { useState, useEffect } from 'react';
import { Sparkles, Clock, AlertCircle, Mail, Coffee, Gavel, Stethoscope, Car, Construction } from 'lucide-react';

const ENGAGEMENT_MESSAGES = {
  salud: [
    "👨‍⚕️ El experto en salud pública está revisando tu solicitud... ¡y prometió no recetarte más trámites!",
    "🥗 Verificando que tu jornada de manipulación de alimentos cumpla con la norma... ¡sin sal ni pimienta!",
    "📋 El jurista está asegurando que tu derecho de petición tenga más fundamentos que una buena arepa.",
    "⏳ Tu caso es importante. Mientras esperas, ¿sabías que Cali tiene más de 300 JAC? ¡La tuya es especial!"
  ],
  movilidad: [
    "🚗 El experto en tránsito está revisando tu comparendo... ¡y promete no ponerte más multas hoy!",
    "📸 Verificando que la foto-multa tenga mejor ángulo que tu selfie de perfil... 🤳",
    "⚖️ El abogado está asegurando que tu derecho de petición tenga más argumentos que un taxi en hora pico.",
    "🚦 Tu caso está en la 'luz verde' del sistema. ¡Pronto tendrás respuesta!"
  ],
  infraestructura: [
    "🚜 La maquinaria virtual ya está en camino... ¡la real también, prometido!",
    "🗺️ El ingeniero está ubicando tu reporte en el mapa... ¡y marcando la ruta más rápida!",
    "🚧 Tu solicitud tiene prioridad 'urgente'. Mientras esperas, imagina que ya hay conos de señalización virtuales. 🟠",
    "⚡ El sistema está trabajando más rápido que un electricista en apagón... ¡casi listo!"
  ],
  default: [
    "🤖 Orbital Prime está pensando... y créenos, piensa más rápido que un caleño en salsa.",
    "📚 El bibliotecario jurídico está buscando la ley exacta para tu caso... ¡sin hacer 'shhh'!",
    "☕ Nuestro café está caliente, tu caso también. ¡Pronto tendrás respuesta!",
    "🎯 Apuntando a la respuesta perfecta... como un arquero en el Pascual.",
    "🔍 Revisando cada detalle con más cuidado que tu abuela al lavar la loza."
  ]
};

export const EngagementStatus = ({ isProcessing, stage, problemType = 'default', elapsedTime = 0 }) => {
  const [currentMessage, setCurrentMessage] = useState('');
  const [showExtendedDelay, setShowExtendedDelay] = useState(false);

  useEffect(() => {
    if (!isProcessing) return;

    const messages = ENGAGEMENT_MESSAGES[problemType] || ENGAGEMENT_MESSAGES.default;
    let index = 0;
    setCurrentMessage(messages[0]);

    const interval = setInterval(() => {
      index++;
      setCurrentMessage(messages[index % messages.length]);
    }, 5000);

    return () => clearInterval(interval);
  }, [isProcessing, problemType]);

  useEffect(() => {
    if (elapsedTime > 90) {
      setShowExtendedDelay(true);
    }
  }, [elapsedTime]);

  if (!isProcessing) return null;

  const getStageIcon = () => {
    switch (problemType) {
      case 'salud': return <Stethoscope className="w-4 h-4 text-rose-500" />;
      case 'movilidad': return <Car className="w-4 h-4 text-blue-500" />;
      case 'infraestructura': return <Construction className="w-4 h-4 text-amber-500" />;
      default: return <Gavel className="w-4 h-4 text-indigo-500" />;
    }
  };

  const getProgressWidth = () => {
    switch (stage) {
      case 'analyzing': return '25%';
      case 'auditing': return '55%';
      case 'generating': return '85%';
      case 'finalizing': return '95%';
      default: return '10%';
    }
  };

  return (
    <div className="w-full max-w-md mx-auto animate-in fade-in zoom-in duration-500">
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xl shadow-indigo-900/5 relative overflow-hidden">
        
        {/* Barra de progreso sutil */}
        <div className="absolute top-0 left-0 w-full h-1 bg-slate-50">
          <div 
            className="h-full bg-indigo-600 transition-all duration-1000 ease-out"
            style={{ width: getProgressWidth() }}
          />
        </div>

        <div className="flex flex-col items-center text-center space-y-4">
          <div className="relative">
            <div className="w-12 h-12 rounded-full bg-indigo-50 flex items-center justify-center animate-bounce">
               {getStageIcon()}
            </div>
            <div className="absolute -top-1 -right-1">
              <Sparkles className="w-4 h-4 text-amber-400 animate-pulse" />
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-[13px] font-bold text-slate-800 leading-tight min-h-[40px] flex items-center justify-center">
              {currentMessage}
            </p>
            <div className="flex items-center justify-center gap-2">
                <Clock className="w-3 h-3 text-slate-400" />
                <p className="text-[9px] font-black uppercase tracking-widest text-slate-400">
                    Tiempo Transcurrido: {Math.floor(elapsedTime)}s
                </p>
            </div>
          </div>

          {showExtendedDelay && (
            <div className="mt-4 p-3 bg-amber-50 border border-amber-100 rounded-xl flex items-start gap-3 text-left animate-in slide-in-from-top-2">
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-[10px] font-bold text-amber-900 leading-tight">
                  Estamos experimentando alta demanda en el motor jurídico.
                </p>
                <p className="text-[9px] text-amber-700 mt-1">
                  Tu solicitud está segura. Si prefieres, podemos avisarte por correo cuando el radicado esté listo.
                </p>
                <button className="mt-2 text-[9px] font-black uppercase tracking-widest text-amber-800 flex items-center gap-1 hover:underline">
                  <Mail className="w-3 h-3" /> Notificarme al correo
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
