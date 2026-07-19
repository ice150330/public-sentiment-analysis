import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

/**
 * 子视图与 URL ?view= 双向同步。
 * 非法或缺失的 view 值回退到 defaultKey（缺省取第一个）。
 */
export function useSubView<T extends string>(keys: readonly T[], defaultKey?: T) {
  const [searchParams, setSearchParams] = useSearchParams();

  const activeView = useMemo<T>(() => {
    const raw = searchParams.get('view') as T | null;
    if (raw && keys.includes(raw)) return raw;
    return defaultKey ?? keys[0];
  }, [searchParams, keys, defaultKey]);

  const setActiveView = useCallback(
    (key: T) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set('view', key);
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  return [activeView, setActiveView] as const;
}
