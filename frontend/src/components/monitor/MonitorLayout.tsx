import React from 'react';
import { useScreenAdapt, DESIGN_WIDTH, DESIGN_HEIGHT } from '@/hooks/useScreenAdapt';

interface MonitorLayoutProps {
  children: React.ReactNode;
}

const MonitorLayout: React.FC<MonitorLayoutProps> = ({ children }) => {
  const containerRef = useScreenAdapt();

  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        background: '#e8ecf1',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      <div
        ref={containerRef}
        style={{
          width: DESIGN_WIDTH,
          height: DESIGN_HEIGHT,
          background: '#f5f7fa',
          padding: 16,
          boxSizing: 'border-box',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        {children}
      </div>
    </div>
  );
};

export default MonitorLayout;
