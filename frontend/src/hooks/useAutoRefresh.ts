/** 自动数据刷新 Hook */
import { useEffect, useRef, useState, useCallback } from 'react';

interface UseAutoRefreshOptions<T> {
  fetcher: () => Promise<T>;
  interval?: number; // ms
  enabled?: boolean;
  onError?: (err: Error) => void;
}

export function useAutoRefresh<T>(options: UseAutoRefreshOptions<T>) {
  const { fetcher, interval = 30000, enabled = true, onError } = options;
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetcher();
      setData(result);
      setLastUpdated(new Date());
    } catch (err) {
      onError?.(err as Error);
    } finally {
      setLoading(false);
    }
  }, [fetcher, onError]);

  useEffect(() => {
    if (!enabled) return;
    refresh();
    timerRef.current = setInterval(refresh, interval);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [enabled, interval, refresh]);

  return { data, loading, lastUpdated, refresh };
}
