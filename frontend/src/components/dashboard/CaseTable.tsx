import React from 'react';
import { ConfidenceBadge } from './ConfidenceBadge';
import { useDashboardStore } from '../../store/useDashboardStore';
import { Search, Filter, ArrowUpDown, MoreHorizontal, Clock, AlertCircle } from 'lucide-react';

interface Case {
  id: string;
  radicado: string;
  user_cc: string;
  asunto: string;
  dependencia_id: string;
  confidence_score: number;
  urgencia_flag: string;
  created_at: string;
  estado: string;
}

interface CaseTableProps {
  cases: Case[];
  isLoading: boolean;
  onRowClick?: (sessionId: string) => void;
}

export const CaseTable: React.FC<CaseTableProps> = ({ cases, isLoading, onRowClick }) => {
  const { selectedIds, toggleSelect, selectAll, clearSelection } = useDashboardStore();

  const handleSelectAll = () => {
    if (selectedIds.length === cases.length) {
      clearSelection();
    } else {
      selectAll(cases.map((c) => c.id));
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs uppercase bg-gray-50 dark:bg-gray-800/50 text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
            <tr>
              <th className="px-4 py-3 w-10">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  checked={cases.length > 0 && selectedIds.length === cases.length}
                  onChange={handleSelectAll}
                />
              </th>
              <th className="px-4 py-3 font-semibold">
                <div className="flex items-center gap-1 cursor-pointer hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
                  Radicado <ArrowUpDown size={14} />
                </div>
              </th>
              <th className="px-4 py-3 font-semibold">Asunto</th>
              <th className="px-4 py-3 font-semibold">Dependencia</th>
              <th className="px-4 py-3 font-semibold">
                <div className="flex items-center gap-1 cursor-pointer hover:text-gray-700 dark:hover:text-gray-200 transition-colors">
                  Confianza <ArrowUpDown size={14} />
                </div>
              </th>
              <th className="px-4 py-3 font-semibold">SLA / Tiempo</th>
              <th className="px-4 py-3 font-semibold text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {cases.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-gray-500">
                  No se encontraron casos con los filtros aplicados.
                </td>
              </tr>
            ) : (
              cases.map((item) => (
                <tr 
                  key={item.id} 
                  onClick={() => onRowClick && onRowClick(item.id)}
                  className="hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors group cursor-pointer"
                >
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      checked={selectedIds.includes(item.id)}
                      onChange={() => toggleSelect(item.id)}
                    />
                  </td>
                  <td className="px-4 py-3 font-mono font-medium text-blue-600 dark:text-blue-400">
                    {item.radicado}
                    {item.urgencia_flag === "VITAL" && (
                      <span className="ml-2 inline-flex items-center text-red-500" title="URGENCIA VITAL">
                        <AlertCircle size={14} />
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 max-w-xs truncate" title={item.asunto}>
                    {item.asunto}
                  </td>
                  <td className="px-4 py-3">
                    <span className="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded text-xs">
                      {item.dependencia_id}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <ConfidenceBadge score={item.confidence_score} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                      <Clock size={14} />
                      <span>14d</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                      <MoreHorizontal size={18} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="px-4 py-3 bg-gray-50 dark:bg-gray-800/30 border-t border-gray-200 dark:border-gray-800 flex items-center justify-between text-xs text-gray-500">
        <div>
          Mostrando {cases.length} resultados
        </div>
        <div className="flex gap-2">
          <button className="px-3 py-1 border border-gray-300 dark:border-gray-700 rounded bg-white dark:bg-gray-900 disabled:opacity-50">Anterior</button>
          <button className="px-3 py-1 border border-gray-300 dark:border-gray-700 rounded bg-white dark:bg-gray-900 disabled:opacity-50">Siguiente</button>
        </div>
      </div>
    </div>
  );
};
