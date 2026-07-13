import React from 'react';

interface FlylineNode {
  id: string;
  name: string;
  x: number;
  y: number;
  size?: number;
}

interface FlylineEdge {
  from: string;
  to: string;
  value?: number;
}

interface FlylineMapProps {
  nodes: FlylineNode[];
  edges: FlylineEdge[];
  width?: number;
  height?: number;
}

export const FlylineMap: React.FC<FlylineMapProps> = ({
  nodes,
  edges,
  width = 400,
  height = 240,
}) => {
  const nodeMap = new Map(nodes.map(n => [n.id, n]));

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: '100%' }}>
      <defs>
        <linearGradient id="flyline-blue" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#1890ff" stopOpacity="0" />
          <stop offset="50%" stopColor="#1890ff" stopOpacity="0.6" />
          <stop offset="100%" stopColor="#1890ff" stopOpacity="0" />
        </linearGradient>
        <filter id="node-glow">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* 基础连线 */}
      {edges.map((edge, i) => {
        const from = nodeMap.get(edge.from);
        const to = nodeMap.get(edge.to);
        if (!from || !to) return null;
        return (
          <line
            key={`base-${i}`}
            x1={from.x} y1={from.y}
            x2={to.x} y2={to.y}
            stroke="#e8e8e8"
            strokeWidth="1"
          />
        );
      })}

      {/* 飞线动画 */}
      {edges.map((edge, i) => {
        const from = nodeMap.get(edge.from);
        const to = nodeMap.get(edge.to);
        if (!from || !to) return null;
        return (
          <line
            key={`fly-${i}`}
            x1={from.x} y1={from.y}
            x2={to.x} y2={to.y}
            stroke="url(#flyline-blue)"
            strokeWidth="2"
            strokeDasharray="10 50"
          >
            <animate
              attributeName="stroke-dashoffset"
              from="60"
              to="-10"
              dur={`${2 + (i % 3) * 0.5}s`}
              repeatCount="indefinite"
            />
          </line>
        );
      })}

      {/* 节点 */}
      {nodes.map(node => (
        <g key={node.id}>
          <circle
            cx={node.x}
            cy={node.y}
            r={(node.size || 20) * 1.5}
            fill="#1890ff"
            opacity="0.12"
            filter="url(#node-glow)"
          />
          <circle
            cx={node.x}
            cy={node.y}
            r={node.size || 8}
            fill="#1890ff"
          />
          <text
            x={node.x}
            y={node.y + (node.size || 8) + 14}
            textAnchor="middle"
            fill="#666"
            fontSize="10"
          >
            {node.name}
          </text>
        </g>
      ))}
    </svg>
  );
};
