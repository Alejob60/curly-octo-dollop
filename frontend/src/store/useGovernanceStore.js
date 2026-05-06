// src/store/useGovernanceStore.js
import { create } from 'zustand';

export const useGovernanceStore = create((set, get) => ({
  cases: [],
  filters: {
    search: '',
    dateFrom: '',
    dateTo: '',
    priority: 'all',
    dependency: 'all'
  },
  selectedCase: null,

  setFilters: (newFilters) => set((state) => ({ filters: { ...state.filters, ...newFilters } })),
  selectCase: (caso) => set({ selectedCase: caso }),
  
  // Simula merge inteligente (en producción usarías WebSockets para push)
  updateCases: (newCases) => set((state) => {
    const updated = [...state.cases];
    newCases.forEach(nc => {
      const idx = updated.findIndex(c => c.radicado === nc.radicado);
      if (idx >= 0) updated[idx] = nc; else updated.push(nc);
    });
    return { cases: updated };
  }),

  // Lógica de filtrado en tiempo real
  getFilteredCases: () => {
    const { cases, filters } = get();
    return cases.filter(c => {
      const matchSearch = !filters.search || 
        c.radicado.toLowerCase().includes(filters.search.toLowerCase()) ||
        c.citizenName.toLowerCase().includes(filters.search.toLowerCase());
      const matchDep = filters.dependency === 'all' || c.dependencyId === filters.dependency;
      const matchPrio = filters.priority === 'all' || c.riskLevel === filters.priority;
      
      // Filtro de fecha básico (puedes usar date-fns para precisión)
      const matchDate = (!filters.dateFrom || c.createdAt >= filters.dateFrom) &&
                        (!filters.dateTo || c.createdAt <= filters.dateTo);

      return matchSearch && matchDep && matchPrio && matchDate;
    });
  }
}));
