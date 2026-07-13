import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { registerWhiteTheme } from '@/theme/echartsWhite';

registerWhiteTheme(echarts);

interface BaseChartProps {
  options: echarts.EChartsOption;
  height?: number;
  onClick?: (params: any) => void;
}

const BaseChart: React.FC<BaseChartProps> = ({ options, height = 260, onClick }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    chartInstance.current = echarts.init(chartRef.current, 'white');
    if (onClick) chartInstance.current.on('click', onClick);

    const handleResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chartInstance.current?.dispose();
    };
  }, [onClick]);

  useEffect(() => {
    chartInstance.current?.setOption(options, true);
  }, [options]);

  return <div ref={chartRef} style={{ width: '100%', height }} />;
};

export default BaseChart;
