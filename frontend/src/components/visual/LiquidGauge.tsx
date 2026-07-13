import React from 'react';

interface LiquidGaugeProps {
  value: number; // 0-100
  title?: string;
  size?: number;
  color?: string;
}

export const LiquidGauge: React.FC<LiquidGaugeProps> = ({
  value,
  title,
  size = 120,
  color = '#1890ff',
}) => {
  const waveHeight = 100 - value;
  const half = size / 2;
  const r = half - 8;

  return (
    <svg viewBox={`0 0 ${size} ${size}`} style={{ width: size, height: size }}>
      <defs>
        <clipPath id={`wave-clip-${value}`}>
          <rect x={half - r} y={half - r + (waveHeight / 100) * (2 * r)} width={2 * r} height={2 * r} />
        </clipPath>
        <linearGradient id={`water-${value}`} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#69c0ff" stopOpacity="0.8" />
          <stop offset="100%" stopColor="#1890ff" stopOpacity="0.4" />
        </linearGradient>
      </defs>

      {/* 外圆 */}
      <circle cx={half} cy={half} r={r} fill="none" stroke="#e8e8e8" strokeWidth="3" />
      {/* 水位 */}
      <circle cx={half} cy={half} r={r - 2} fill={`url(#water-${value})`} clipPath={`url(#wave-clip-${value})`}>
        <animateTransform
          attributeName="transform"
          type="translate"
          values="-2,0; 2,0; -2,0"
          dur="3s"
          repeatCount="indefinite"
        />
      </circle>
      {/* 数值 */}
      <text x={half} y={half - 5} textAnchor="middle" fill="#1890ff" fontSize={size * 0.22} fontWeight="bold">
        {value}%
      </text>
      {title && (
        <text x={half} y={half + 14} textAnchor="middle" fill="#999" fontSize={size * 0.1}>
          {title}
        </text>
      )}
    </svg>
  );
};
