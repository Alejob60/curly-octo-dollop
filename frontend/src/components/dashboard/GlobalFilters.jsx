// src/components/dashboard/GlobalFilters.jsx
import React, { useEffect, useState, useCallback } from 'react';
import { useGovernanceStore } from '../../store/useGovernanceStore';
import { Search, Filter, Calendar, AlertTriangle, Building2, XCircle } from 'lucide-react';

export default function GlobalFilters() {
  const [localFilters, setLocalFilters] = useState({
    search: '', dateFrom: '', dateTo: '', priority: 'all', dependency: 'all'
  });
  const [dependencies, setDependencies] = useState([]);
  const [isLoadingDeps, setIsLoadingDeps] = useState(true);
  const setFilters = useGovernanceStore((state) => state.setFilters);

  const fetchDependencies = useCallback(async () => {
    try {
      setIsLoadingDeps(true);
      // Fallback for development if API is not yet ready
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/v1/config/dependencies`);
      if (res.ok) {
        const data = await res.json();
        setDependencies(data);
      } else {
        // Mock data for development
        setDependencies([
          { id: '4135', nombre: 'Secretaría de Salud', sector: 'Salud' },
          { id: '4146', nombre: 'Secretaría de Infraestructura', sector: 'Infraestructura' },
          { id: '2201', nombre: 'Secretaría de Educación', sector: 'Educación' }
        ]);
      }
    } catch (err) {
      console.error('Error cargando dependencias:', err);
    } finally {
      setIsLoadingDeps(false);
    }
  }, []);

  useEffect(() => { fetchDependencies(); }, [fetchDependencies]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setLocalFilters(prev => ({ ...prev, [name]: value }));
    setFilters({ [name]: value }); // Sync inmediato con store
  };

  const handleClear = () => {
    const clean = { search: '', dateFrom: '', dateTo: '', priority: 'all', dependency: 'all' };
    setLocalFilters(clean);
    setFilters(clean);
  };

  return (
    <div className="bg-white shadow-sm border-b border-gray-200 p-4 animate-fade-in-down">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <Filter className="w-4 h-4 text-blue-600" /> Filtros Globales
          </h3>
          <button onClick={handleClear} className="text-xs text-red-500 hover:text-red-700 font-medium flex items-center gap-1">
            <XCircle className="w-3 h-3" /> Limpiar
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 font-medium">Buscar (Radicado/CC)</label>
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400" />
              <input name="search" value={localFilters.search} onChange={handleInputChange}
                placeholder="Ej: 2026-00124..." className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none" />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 font-medium">Fecha Inicio</label>
            <div className="relative">
              <Calendar className="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400" />
              <input type="date" name="dateFrom" value={localFilters.dateFrom} onChange={handleInputChange}
                className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none" />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 font-medium">Fecha Fin</label>
            <div className="relative">
              <Calendar className="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400" />
              <input type="date" name="dateTo" value={localFilters.dateTo} onChange={handleInputChange}
                className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none" />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 font-medium">Prioridad</label>
            <div className="relative">
              <AlertTriangle className="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400" />
              <select name="priority" value={localFilters.priority} onChange={handleInputChange}
                className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none appearance-none bg-white">
                <option value="all">🔘 Todas</option>
                <option value="red">🔴 Crítica (Rojo)</option>
                <option value="yellow">🟡 Media (Amarillo)</option>
                <option value="green">🟢 Fácil (Verde)</option>
              </select>
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 font-medium">Dependencia</label>
            <div className="relative">
              <Building2 className="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400" />
              <select name="dependency" value={localFilters.dependency} onChange={handleInputChange} disabled={isLoadingDeps}
                className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none appearance-none bg-white disabled:bg-gray-100">
                <option value="all">🏛️ Todas las Secretarías</option>
                {dependencies.map(dep => (
                  <option key={dep.id} value={dep.id}>{dep.nombre} ({dep.sector})</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
