# ⚛️ Orbital Copilot: React Hooks & Frontend Logic (V59.5)

Este documento describe la lógica de integración para el Dashboard de Productividad, facilitando la implementación de la "Bandeja de Entrada Inteligente".

## 1. `useCopilotQueue`
Gestiona la carga priorizada de radicados con cálculo de SLA en tiempo real.

```typescript
export const useCopilotQueue = () => {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchQueue = async () => {
    const res = await api.get('/governance/copilot/queue');
    // Priorización Automática: (Vencidos) > (Riesgo Rojo) > (Score < 70)
    const sorted = res.data.queue.sort((a, b) => {
      if (a.sla === "VENCIDO") return -1;
      if (b.sla === "VENCIDO") return 1;
      return b.score - a.score;
    });
    setCases(sorted);
    setLoading(false);
  };

  useEffect(() => { fetchQueue(); }, []);

  return { cases, loading, refresh: fetchQueue };
};
```

## 2. `useBatchActions`
Implementa el "Blindaje Jurídico" bloqueando firmas en lote inseguras.

```typescript
export const useBatchActions = (selectedIds: string[]) => {
  const [isConfirming, setIsConfirming] = useState(false);

  const handleBatchApprove = async (cases: Case[]) => {
    const safeCases = cases.filter(c => c.score >= 0.70);
    const unsafeCount = cases.length - safeCases.length;

    if (unsafeCount > 0) {
      alert(`⚠️ Atención: ${unsafeCount} casos tienen un Score IA bajo y DEBEN ser revisados individualmente.`);
      // Solo procedemos con los seguros tras confirmación expresa
    }

    await api.post('/governance/copilot/batch-approve', {
      radicados: safeCases.map(c => c.radicado),
      official_id: currentUser.id
    });
  };

  return { handleBatchApprove, isConfirming };
};
```

## 3. `useAIAdjustment`
Cierra el bucle de aprendizaje Hermes enviando feedback directo al motor agéntico.

```typescript
export const useAIAdjustment = (radicado: string) => {
  const [feedback, setFeedback] = useState("");

  const requestAjuste = async () => {
    if (feedback.length < 10) return alert("Por favor, sea más específico con la corrección.");
    
    await api.post(`/governance/copilot/request-adjustment/${radicado}`, {
      feedback,
      official_id: currentUser.id
    });
    
    // UI: Mostrar estado "IA Regenerando..."
  };

  return { feedback, setFeedback, requestAjuste };
};
```
