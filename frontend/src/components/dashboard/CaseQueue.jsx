// src/components/dashboard/CaseQueue.jsx
import React from 'react';
import { useGovernanceStore } from '../../store/useGovernanceStore';
import CaseCard from './CaseCard';

export default function CaseQueue() {
  const getFilteredCases = useGovernanceStore(s => s.getFilteredCases);
  const filtered = getFilteredCases();

  if (filtered.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <p className="text-lg">No hay casos que coincidan con los filtros</p>
        <p className="text-sm">Ajusta los criterios o espera nuevas radicaciones</p>
      </div>
    );
  }

  return (
    <div className="space-y-2 animate-fade-in">
      {filtered.map(caso => (
        <CaseCard key={caso.radicado} caso={caso} />
      ))}
    </div>
  );
}
