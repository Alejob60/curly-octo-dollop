// src/components/dashboard/CaseCard.jsx
import React from 'react';
import { useGovernanceStore } from '../../store/useGovernanceStore';

export default function CaseCard({ caso }) {
  const selectCase = useGovernanceStore(s => s.selectCase);
  
  const isGreen = caso.confidence >= 90;
  const isYellow = caso.confidence >= 60 && caso.confidence < 90;
  const isRed = caso.confidence < 60;

  const borderColor = isGreen ? 'border-green-500' : isYellow ? 'border-yellow-500' : 'border-red-500';
  const bgColor = isGreen ? 'bg-green-50' : isYellow ? 'bg-yellow-50' : 'bg-red-50';
  const textColor = isGreen ? 'text-green-700' : isYellow ? 'text-yellow-700' : 'text-red-700';

  return (
    <div onClick={() => selectCase(caso)}
      className={`p-4 mb-3 rounded-lg border-l-4 shadow-sm cursor-pointer hover:shadow-md transition transform hover:-translate-y-0.5 ${bgColor} ${borderColor}`}>
      
      <div className="flex justify-between items-start">
        <div>
          <span className="text-xs font-mono bg-gray-200 px-2 py-1 rounded">{caso.radicado}</span>
          <h3 className="font-semibold mt-1 text-gray-900">{caso.citizenName}</h3>
          <p className="text-sm text-gray-600">{caso.dependencyName}</p>
        </div>
        <div className="text-right">
          <div className={`text-lg font-bold ${textColor}`}>{caso.confidence}%</div>
          <span className="text-xs text-gray-500">Confianza IA</span>
        </div>
      </div>

      <div className="mt-3 flex justify-between items-center">
        <span className="text-xs font-medium bg-blue-100 text-blue-800 px-2 py-1 rounded">
          ⏳ SLA: {caso.slaRemaining}h
        </span>
        
        <div className="flex gap-2" onClick={e => e.stopPropagation()}>
          {isGreen && (
            <button className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 transition">
              📦 Aprobar Lote
            </button>
          )}
          {isYellow && (
            <button className="bg-yellow-600 text-white px-3 py-1 rounded text-sm hover:bg-yellow-700 transition">
              👁️ Revisar
            </button>
          )}
          {isRed && (
            <button className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 transition">
              ✍️ Intervención
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
