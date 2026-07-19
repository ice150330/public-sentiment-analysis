import React from 'react';
import { Tag } from 'antd';

/** 预警级别色彩映射：P1 红 / P2 橙 / P3 蓝 / P4 灰 */
const SEVERITY_COLORS: Record<string, string> = {
  P1: 'var(--negative)',
  P2: 'var(--warning)',
  P3: 'var(--primary)',
  P4: 'var(--neutral)',
};

export const severityColor = (severity?: string | null) =>
  SEVERITY_COLORS[(severity || '').toUpperCase()] || 'var(--neutral)';

const SeverityTag: React.FC<{ severity?: string | null }> = ({ severity }) => {
  const value = (severity || 'P4').toUpperCase();
  return (
    <Tag
      className="psa-tag"
      style={{
        color: '#fff',
        background: severityColor(value),
        borderColor: 'transparent',
        fontWeight: 800,
      }}
    >
      {value}
    </Tag>
  );
};

export default SeverityTag;
