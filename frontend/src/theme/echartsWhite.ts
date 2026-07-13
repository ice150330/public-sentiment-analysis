/** ECharts 白色大屏主题 - 适配 Ant Design 白色风格 */
const whiteTheme = {
  color: ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#eb2f96', '#fadb14'],
  backgroundColor: 'transparent',
  textStyle: { color: '#333', fontSize: 12 },
  title: {
    textStyle: { color: '#1a1a2e', fontSize: 16, fontWeight: 'bold' },
    subtextStyle: { color: '#666' },
    top: 8,
    left: 16,
  },
  legend: {
    top: 8,
    right: 16,
    textStyle: { color: '#666', fontSize: 11 },
    itemWidth: 12,
    itemHeight: 8,
  },
  tooltip: {
    backgroundColor: 'rgba(255, 255, 255, 0.96)',
    borderColor: '#e8e8e8',
    borderWidth: 1,
    textStyle: { color: '#333', fontSize: 12 },
    padding: [8, 12],
    extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-radius: 4px;',
  },
  grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
  categoryAxis: {
    axisLine: { show: true, lineStyle: { color: '#e8e8e8' } },
    axisTick: { show: false },
    axisLabel: { color: '#999', fontSize: 11 },
    splitLine: { show: true, lineStyle: { color: '#f0f0f0', type: 'dashed' } },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#999', fontSize: 11 },
    splitLine: { show: true, lineStyle: { color: '#f0f0f0', type: 'dashed' } },
  },
  pie: {
    radius: ['45%', '70%'],
    center: ['50%', '55%'],
    label: { color: '#666', fontSize: 11 },
    emphasis: {
      label: { fontSize: 14, fontWeight: 'bold' },
      itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.1)' },
    },
  },
  radar: {
    indicatorName: { color: '#666', fontSize: 11 },
    splitArea: { areaStyle: { color: ['rgba(24,144,255,0.02)', 'rgba(24,144,255,0.05)'] } },
    axisLine: { lineStyle: { color: '#e8e8e8' } },
    splitLine: { lineStyle: { color: '#e8e8e8' } },
  },
};

export default whiteTheme;
export const registerWhiteTheme = (echarts: any) => {
  echarts.registerTheme('white', whiteTheme);
};
