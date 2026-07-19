export const formatDateTime = (value?: string | null) => {
  if (!value) return '暂无';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export const formatNumber = (value?: number | null) => {
  if (value === null || value === undefined) return '暂无';
  return new Intl.NumberFormat('zh-CN').format(value);
};

export const sentimentText = (label?: string) => {
  if (label === 'positive') return '正面';
  if (label === 'negative') return '负面';
  if (label === 'neutral') return '中性';
  return label || '未知';
};

export const platformTone = (name?: string | null) => {
  const normalized = (name || '').toLowerCase();
  if (normalized.includes('微博') || normalized.includes('weibo')) return 'weibo';
  if (normalized.includes('抖音') || normalized.includes('douyin')) return 'douyin';
  if (normalized.includes('头条') || normalized.includes('toutiao')) return 'toutiao';
  if (normalized.includes('百度') || normalized.includes('baidu')) return 'baidu';
  if (normalized.includes('b站') || normalized.includes('bilibili')) return 'bilibili';
  if (normalized.includes('知乎') || normalized.includes('zhihu')) return 'zhihu';
  return 'neutral';
};
