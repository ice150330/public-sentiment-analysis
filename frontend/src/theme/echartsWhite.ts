/** ECharts 浅色主题 - 对齐 pen/UI.pen 设计令牌 */
const lightTheme = {
  color: ['#2563EB', '#16A34A', '#F59E0B', '#E11D48', '#0EA5E9', '#64748B', '#3B82F6', '#F43F5E'],
  backgroundColor: 'transparent',
  textStyle: { color: '#64748B', fontSize: 12, fontFamily: 'Inter, "Noto Sans SC", sans-serif' },
  title: {
    textStyle: { color: '#152033', fontSize: 15, fontWeight: 800 },
    subtextStyle: { color: '#64748B' },
    top: 8,
    left: 16,
  },
  legend: {
    top: 8,
    right: 16,
    textStyle: { color: '#64748B', fontSize: 11 },
    itemWidth: 12,
    itemHeight: 8,
    icon: 'roundRect',
  },
  tooltip: {
    backgroundColor: 'rgba(255, 255, 255, 0.97)',
    borderColor: '#D7E1EC',
    borderWidth: 1,
    textStyle: { color: '#152033', fontSize: 12 },
    padding: [8, 12],
    extraCssText: 'box-shadow: 0 12px 28px -14px rgba(32, 70, 111, 0.28); border-radius: 10px;',
  },
  grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
  categoryAxis: {
    axisLine: { show: true, lineStyle: { color: '#D7E1EC' } },
    axisTick: { show: false },
    axisLabel: { color: '#94A3B8', fontSize: 11 },
    splitLine: { show: false },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#94A3B8', fontSize: 11 },
    splitLine: { show: true, lineStyle: { color: '#EEF3F8', type: 'dashed' } },
  },
  pie: {
    radius: ['45%', '70%'],
    center: ['50%', '55%'],
    label: { color: '#64748B', fontSize: 11 },
    itemStyle: { borderColor: '#fff', borderWidth: 2 },
    emphasis: {
      label: { fontSize: 14, fontWeight: 'bold' },
      itemStyle: { shadowBlur: 12, shadowOffsetX: 0, shadowColor: 'rgba(21, 32, 51, 0.18)' },
    },
  },
  radar: {
    indicatorName: { color: '#64748B', fontSize: 11 },
    splitArea: { areaStyle: { color: ['rgba(37, 99, 235, 0.03)', 'rgba(37, 99, 235, 0.06)'] } },
    axisLine: { lineStyle: { color: '#D7E1EC' } },
    splitLine: { lineStyle: { color: '#D7E1EC' } },
  },
};

export default lightTheme;
export const registerWhiteTheme = (echarts: any) => {
  echarts.registerTheme('white', lightTheme);
};
