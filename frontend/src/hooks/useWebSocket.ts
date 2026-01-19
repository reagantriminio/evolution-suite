import { useEffect, useRef, useCallback } from 'react';
import { useAgentStore } from '@/stores/agentStore';
import type { WebSocketEvent } from '@/lib/types';

const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const storeRef = useRef(useAgentStore.getState());
  // Track if we're intentionally closing (cleanup) vs unexpected disconnect
  const isCleaningUpRef = useRef(false);

  // Keep storeRef current without causing re-renders
  useEffect(() => {
    return useAgentStore.subscribe((state) => {
      storeRef.current = state;
    });
  }, []);

  const connect = useCallback(() => {
    // Don't connect if we're in cleanup phase
    if (isCleaningUpRef.current) {
      return;
    }

    // Clean up any pending reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Clean up existing connection
    if (wsRef.current) {
      // Mark as intentional close to prevent reconnect loop
      const oldWs = wsRef.current;
      wsRef.current = null;
      oldWs.onclose = null; // Remove handler before closing
      oldWs.close();
    }

    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('[WS] Connected');
      storeRef.current.setConnected(true);
    };

    ws.onclose = () => {
      console.log('[WS] Disconnected');
      storeRef.current.setConnected(false);

      // Only reconnect if this wasn't an intentional cleanup
      if (!isCleaningUpRef.current && wsRef.current === ws) {
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('[WS] Reconnecting...');
          connect();
        }, 2000);
      }
    };

    ws.onerror = (error) => {
      console.error('[WS] Error:', error);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Respond to ping with pong for keepalive
        if (data.type === 'ping') {
          ws.send(JSON.stringify({ type: 'pong' }));
          return;
        }
        storeRef.current.handleEvent(data as WebSocketEvent);
      } catch (error) {
        console.error('[WS] Failed to parse message:', error);
      }
    };

    wsRef.current = ws;
  }, []);

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
    isCleaningUpRef.current = false;
    connect();

    return () => {
      // Mark that we're intentionally cleaning up
      isCleaningUpRef.current = true;

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent reconnect on intentional close
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return {
    send,
    injectGuidance,
    updatePrompt,
  };
}
