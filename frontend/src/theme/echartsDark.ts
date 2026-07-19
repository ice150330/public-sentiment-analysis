/** ECharts 暗色主题 - 数据大屏专用，与浅色版共享品牌色板 */
const darkTheme = {
  color: ['#3B82F6', '#22C55E', '#F59E0B', '#F43F5E', '#38BDF8', '#94A3B8', '#818CF8', '#FB7185'],
  backgroundColor: 'transparent',
  textStyle: { color: '#94A3B8', fontSize: 12, fontFamily: 'Inter, "Noto Sans SC", sans-serif' },
  title: {
    textStyle: { color: '#E2E8F0', fontSize: 15, fontWeight: 800 },
    subtextStyle: { color: '#64748B' },
    top: 8,
    left: 16,
  },
  legend: {
    top: 8,
    right: 16,
    textStyle: { color: '#94A3B8', fontSize: 11 },
    itemWidth: 12,
    itemHeight: 8,
    icon: 'roundRect',
  },
  tooltip: {
    backgroundColor: 'rgba(15, 27, 45, 0.96)',
    borderColor: '#1E3A5F',
    borderWidth: 1,
    textStyle: { color: '#E2E8F0', fontSize: 12 },
    padding: [8, 12],
    extraCssText: 'box-shadow: 0 12px 28px -10px rgba(0, 0, 0, 0.55); border-radius: 10px;',
  },
  grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
  categoryAxis: {
    axisLine: { show: true, lineStyle: { color: '#1E3A5F' } },
    axisTick: { show: false },
    axisLabel: { color: '#64748B', fontSize: 11 },
    splitLine: { show: false },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#64748B', fontSize: 11 },
    splitLine: { show: true, lineStyle: { color: 'rgba(30, 58, 95, 0.5)', type: 'dashed' } },
  },
  pie: {
    radius: ['45%', '70%'],
    center: ['50%', '55%'],
    label: { color: '#94A3B8', fontSize: 11 },
    itemStyle: { borderColor: '#0B1220', borderWidth: 2 },
    emphasis: {
      label: { fontSize: 14, fontWeight: 'bold', color: '#E2E8F0' },
      itemStyle: { shadowBlur: 14, shadowOffsetX: 0, shadowColor: 'rgba(59, 130, 246, 0.35)' },
    },
  },
  radar: {
    indicatorName: { color: '#94A3B8', fontSize: 11 },
    splitArea: { areaStyle: { color: ['rgba(59, 130, 246, 0.04)', 'rgba(59, 130, 246, 0.08)'] } },
    axisLine: { lineStyle: { color: '#1E3A5F' } },
    splitLine: { lineStyle: { color: '#1E3A5F' } },
  },
};

export default darkTheme;
export const registerDarkTheme = (echarts: any) => {
  echarts.registerTheme('psa-dark', darkTheme);
};
