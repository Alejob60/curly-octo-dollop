import { useState, useEffect, useRef, useCallback } from 'react';

export function useChatSocket(sessionId) {
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const socketRef = useRef(null);

  useEffect(() => {
    if (!sessionId) return;

    const wsUrl = import.meta.env.VITE_WS_URL_CHAT || `ws://localhost:8000/api/v1/chat/ws/${sessionId}`;
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log('✅ Chat WebSocket Connected');
      setIsConnected(true);
    };

    socket.onmessage = (event) => {
      const text = event.data;
      setMessages(prev => [...prev, {
        role: "assistant",
        content: text,
        timestamp: new Date().toLocaleTimeString()
      }]);
      setIsTyping(false);
    };

    socket.onclose = () => {
      console.log('❌ Chat WebSocket Disconnected');
      setIsConnected(false);
    };

    return () => {
      socket.close();
    };
  }, [sessionId]);

  const sendMessage = useCallback((text) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      setMessages(prev => [...prev, {
        role: "user",
        content: text,
        timestamp: new Date().toLocaleTimeString()
      }]);
      socketRef.current.send(text);
      setIsTyping(true);
    }
  }, []);

  return { messages, isConnected, isTyping, sendMessage, setMessages };
}
