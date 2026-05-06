import { useState, useEffect, useCallback } from 'react';

export function useGovernanceSocket() {
  const [metrics, setMetrics] = useState({ confidence: 94, delayDaysPrevented: 124, fiscalSavings: 450, alerts: 3 });
  const [liveActivity, setLiveActivity] = useState([]);
  const [statusLane, setStatusLane] = useState('green');
  const [isConnected, setIsConnected] = useState(false);
  const [infraStatus, setInfraStatus] = useState(null);

  useEffect(() => {
    const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    
    const fetchInfra = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/governance/infra-status`);
        const data = await res.json();
        setInfraStatus(data);
      } catch (e) {
        console.error("Error fetching infra status:", e);
      }
    };
    
    fetchInfra();
    const interval = setInterval(fetchInfra, 30000); // Actualizar cada 30s

    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1/governance/stream';
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log('✅ Connected to Governance Stream');
      setIsConnected(true);
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'INITIAL_METRICS') {
        setMetrics({
          confidence: data.confidence,
          delayDaysPrevented: data.delayDaysPrevented,
          fiscalSavings: data.fiscalSavings,
          alerts: data.alerts
        });
        setStatusLane(data.statusLane || 'green');
      } else if (data.type === 'LIVE_ACTIVITY') {
        setLiveActivity(prev => [data, ...prev].slice(0, 5));
      }
    };

    socket.onclose = () => {
      console.log('❌ Disconnected from Governance Stream');
      setIsConnected(false);
    };

    return () => {
      socket.close();
      clearInterval(interval);
    };
  }, []);

  return { metrics, liveActivity, statusLane, isConnected, infraStatus };
}
