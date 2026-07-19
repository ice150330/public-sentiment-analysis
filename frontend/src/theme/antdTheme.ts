import type { ThemeConfig } from 'antd';

/**
 * antd 主题令牌 —— 与 pen/UI.pen 设计变量一一对应。
 * 自定义 psa-* CSS 继续使用 index.css 中的 CSS 变量，此处只负责让 antd 组件融入同一视觉体系。
 */
export const antdTheme: ThemeConfig = {
  token: {
    colorPrimary: '#2563EB',
    colorInfo: '#2563EB',
    colorSuccess: '#16A34A',
    colorWarning: '#F59E0B',
    colorError: '#DC2626',
    colorTextBase: '#152033',
    colorBorder: '#D7E1EC',
    colorBorderSecondary: '#E7EEF7',
    colorBgLayout: '#EEF3F8',
    borderRadius: 12,
    borderRadiusLG: 18,
    borderRadiusSM: 8,
    borderRadiusXS: 6,
    fontFamily: '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
  },
  components: {
    Button: {
      borderRadius: 999,
      controlHeight: 36,
      fontWeight: 700,
    },
    Input: { borderRadius: 10 },
    InputNumber: { borderRadius: 10 },
    Select: { borderRadius: 10 },
    DatePicker: { borderRadius: 10 },
    Table: {
      headerBg: '#F3F7FC',
      headerColor: '#64748B',
      headerSplitColor: 'transparent',
      rowHoverBg: '#F8FBFF',
    },
    Pagination: { borderRadius: 999 },
    Tag: { borderRadiusSM: 999 },
    Segmented: { borderRadius: 12 },
    Card: { borderRadiusLG: 18 },
    Modal: { borderRadiusLG: 18 },
    Message: { borderRadiusLG: 12 },
    Notification: { borderRadiusLG: 12 },
  },
};

export default antdTheme;
