/**
 * @file useRealtime.ts
 * @description WebSocket 实时推送连接 hook
 * @author Kimi Code
 */

import { useCallback, useEffect, useRef, useState } from 'react';

export interface RealtimeMessage {
  type: 'alert' | 'crawl_complete' | 'data_quality' | 'pong';
  payload: Record<string, any>;
  timestamp: string;
}

interface UseRealtimeOptions {
  token: string | null;
  reconnectMaxDelay?: number;
  reconnectBaseDelay?: number;
  maxReconnectAttempts?: number;
}

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const WS_BASE_URL = (process.env.REACT_APP_WS_URL || API_BASE_URL).replace(/^http/, 'ws');

export function useRealtime({
  token,
  reconnectBaseDelay = 1000,
  reconnectMaxDelay = 30000,
  maxReconnectAttempts = 10,
}: UseRealtimeOptions) {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<RealtimeMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const attemptRef = useRef(0);
  const visibilityHandlerRef = useRef<(() => void) | null>(null);

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      window.clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!token) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    clearReconnectTimeout();

    const url = `${WS_BASE_URL}/ws?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      attemptRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as RealtimeMessage;
        if (data.type === 'pong') return;
        setLastMessage(data);
      } catch {
        // ignore malformed message
      }
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      if (attemptRef.current >= maxReconnectAttempts) return;
      const delay = Math.min(
        reconnectBaseDelay * 2 ** attemptRef.current,
        reconnectMaxDelay,
      );
      attemptRef.current += 1;
      reconnectTimeoutRef.current = window.setTimeout(connect, delay);
    };

    ws.onerror = () => {
      // onclose will trigger reconnect
    };
  }, [token, reconnectBaseDelay, reconnectMaxDelay, maxReconnectAttempts, clearReconnectTimeout]);

  const disconnect = useCallback(() => {
    clearReconnectTimeout();
    attemptRef.current = maxReconnectAttempts + 1; // stop reconnecting
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }, [clearReconnectTimeout, maxReconnectAttempts]);

  useEffect(() => {
    if (!token) {
      disconnect();
      return;
    }
    connect();

    const onVisibilityChange = () => {
      if (!document.hidden) {
        if (!connected && attemptRef.current > 0) {
          attemptRef.current = 0;
          connect();
        }
      }
    };
    visibilityHandlerRef.current = onVisibilityChange;
    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange);
      disconnect();
    };
  }, [token, connect, disconnect, connected]);

  return { connected, lastMessage };
}
