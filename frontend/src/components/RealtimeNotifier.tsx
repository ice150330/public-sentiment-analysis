/**
 * @file RealtimeNotifier.tsx
 * @description 全局实时消息通知组件
 * @author Kimi Code
 */

import React, { useEffect, useRef } from 'react';
import { notification } from 'antd';
import { useAuth } from '../auth/AuthContext';
import { getAuthToken } from '../services/api';
import { useRealtime } from '../hooks/useRealtime';

const formatPlatformSummary = (details: any[]): string => {
  if (!Array.isArray(details) || details.length === 0) return '无详情';
  return details
    .filter((d) => d && typeof d === 'object')
    .map((d) => `${d.platform || '未知平台'}: ${d.status || ''} ${d.records ?? ''}`)
    .join(' | ');
};

export const RealtimeNotifier: React.FC = () => {
  const { user } = useAuth();
  const token = user ? getAuthToken() || '' : '';
  const { connected, lastMessage } = useRealtime({ token });
  const notifiedRef = useRef(false);

  useEffect(() => {
    if (connected && !notifiedRef.current) {
      // 首次连接成功可在此记录日志，当前保持静默
      notifiedRef.current = true;
    }
  }, [connected]);

  useEffect(() => {
    if (!lastMessage) return;

    switch (lastMessage.type) {
      case 'alert': {
        const payload = lastMessage.payload || {};
        const severity = payload.severity || 'warning';
        notification.open({
          type: severity === 'critical' ? 'error' : severity === 'high' ? 'warning' : 'info',
          message: `新预警：${payload.rule_name || '未知规则'}`,
          description: `严重级别：${severity}，事件ID：${payload.event_id ?? '-'}`,
          placement: 'topRight',
          duration: 6,
        });
        break;
      }
      case 'crawl_complete': {
        const payload = lastMessage.payload || {};
        notification.success({
          message: '采集完成',
          description: `新增 ${payload.total ?? 0} 条热榜数据；${formatPlatformSummary(payload.details)}`,
          placement: 'topRight',
          duration: 4,
        });
        break;
      }
      case 'data_quality': {
        const payload = lastMessage.payload || {};
        if (payload.issues_found > 0) {
          notification.warning({
            message: '数据质量异常',
            description: `检查批次 ${payload.run_id} 发现 ${payload.issues_found} 个问题，critical ${payload.severity_counts?.critical ?? 0} 个`,
            placement: 'topRight',
            duration: 6,
          });
        }
        break;
      }
      default:
        break;
    }
  }, [lastMessage]);

  return null;
};
