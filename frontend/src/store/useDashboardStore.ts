import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface DashboardFilters {
  status: string;
  dependencyId: string;
  minConfidence: number;
  search: string;
}

interface DashboardState {
  filters: DashboardFilters;
  selectedIds: string[];
  setFilters: (filters: Partial<DashboardFilters>) => void;
  toggleSelect: (id: string) => void;
  selectAll: (ids: string[]) => void;
  clearSelection: () => void;
  resetFilters: () => void;
}

const initialFilters: DashboardFilters = {
  status: 'pending',
  dependencyId: 'all',
  minConfidence: 0,
  search: '',
};

export const useDashboardStore = create<DashboardState>()(
  persist(
    (set) => ({
      filters: initialFilters,
      selectedIds: [],
      
      setFilters: (newFilters) => 
        set((state) => ({ 
          filters: { ...state.filters, ...newFilters },
          selectedIds: [] // Reset selection when filters change
        })),
        
      toggleSelect: (id) => 
        set((state) => ({
          selectedIds: state.selectedIds.includes(id)
            ? state.selectedIds.filter((i) => i !== id)
            : [...state.selectedIds, id],
        })),
        
      selectAll: (ids) => set({ selectedIds: ids }),
      
      clearSelection: () => set({ selectedIds: [] }),
      
      resetFilters: () => set({ filters: initialFilters, selectedIds: [] }),
    }),
    {
      name: 'orbital-dashboard-storage',
    }
  )
);
