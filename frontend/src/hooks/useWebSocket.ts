import { useEffect, useRef, useCallback } from 'react';
import { useAgentStore } from '@/stores/agentStore';
import type { WebSocketEvent } from '@/lib/types';

const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const { setConnected, handleEvent } = useAgentStore();

  const connect = useCallback(() => {
    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('[WS] Connected');
      setConnected(true);
    };

    ws.onclose = () => {
      console.log('[WS] Disconnected');
      setConnected(false);

      // Reconnect after delay
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('[WS] Reconnecting...');
        connect();
      }, 2000);
    };

    ws.onerror = (error) => {
      console.error('[WS] Error:', error);
    };

    ws.onmessage = (event) => {
      try {
        const data: WebSocketEvent = JSON.parse(event.data);
        handleEvent(data);
      } catch (error) {
        console.error('[WS] Failed to parse message:', error);
      }
    };

    wsRef.current = ws;
  }, [setConnected, handleEvent]);

  const send = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const injectGuidance = useCallback((agentId: string, content: string) => {
    send({ type: 'inject_guidance', agentId, content });
  }, [send]);

  const updatePrompt = useCallback((name: string, content: string) => {
    send({ type: 'update_prompt', name, content });
  }, [send]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    send,
    injectGuidance,
    updatePrompt,
  };
}
