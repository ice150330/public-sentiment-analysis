/** 大屏布局 Hook - 基于 scale 的响应式适配 */
import { useEffect, useRef, useCallback } from 'react';

const DESIGN_WIDTH = 1920;
const DESIGN_HEIGHT = 1080;

export function useScreenAdapt() {
  const containerRef = useRef<HTMLDivElement>(null);

  const calcScale = useCallback(() => {
    if (!containerRef.current) return;
    const w = window.innerWidth;
    const h = window.innerHeight;
    const scaleX = w / DESIGN_WIDTH;
    const scaleY = h / DESIGN_HEIGHT;
    const scale = Math.min(scaleX, scaleY);
    const offsetX = (w - DESIGN_WIDTH * scale) / 2;
    const offsetY = (h - DESIGN_HEIGHT * scale) / 2;

    containerRef.current.style.width = `${DESIGN_WIDTH}px`;
    containerRef.current.style.height = `${DESIGN_HEIGHT}px`;
    containerRef.current.style.transform = `scale(${scale})`;
    containerRef.current.style.transformOrigin = '0 0';
    containerRef.current.style.position = 'absolute';
    containerRef.current.style.left = `${offsetX}px`;
    containerRef.current.style.top = `${offsetY}px`;
  }, []);

  useEffect(() => {
    calcScale();
    window.addEventListener('resize', calcScale);
    return () => window.removeEventListener('resize', calcScale);
  }, [calcScale]);

  return containerRef;
}

export { DESIGN_WIDTH, DESIGN_HEIGHT };
