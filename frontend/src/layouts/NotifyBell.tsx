import React, { useCallback, useEffect, useState } from 'react';
import { Badge, Button, Popover } from 'antd';
import { BellOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import {
  AlertEvent,
  AlertSummary,
  getAlertEvents,
  getAlertSummary,
} from '../services/api';
import { formatDateTime } from '../utils/format';

const severityTone = (severity?: string) => {
  const value = (severity || '').toUpperCase();
  if (value === 'P1') return 'danger';
  if (value === 'P2') return 'warning';
  return 'muted';
};

/**
 * 顶栏预警铃铛 —— 对应 pen 组件 Top Bar Bell。
 * 每 60s 轮询一次预警摘要，点击展开最近待处理事件。
 */
export const NotifyBell: React.FC = () => {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<AlertSummary | null>(null);
  const [events, setEvents] = useState<AlertEvent[]>([]);
  const [open, setOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const [summaryRes, eventsRes] = await Promise.all([
        getAlertSummary(),
        getAlertEvents({ status: 'pending', page: 1, page_size: 5 }),
      ]);
      setSummary(summaryRes.data);
      setEvents(eventsRes.data.items);
    } catch {
      // 预警铃铛静默失败，不打扰主流程
    }
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 60000);
    return () => window.clearInterval(timer);
  }, [load]);

  const gotoAlerts = () => {
    setOpen(false);
    navigate('/?view=alerts');
  };

  const panel = (
    <div className="psa-notify-panel">
      <div className="psa-notify-head">
        <strong>预警通知</strong>
        <span className="psa-notify-count">
          待处理 {summary?.pending_count ?? 0}
        </span>
      </div>
      <div className="psa-notify-list">
        {events.length === 0 && (
          <div className="psa-notify-empty">
            <CheckCircleOutlined />
            <span>暂无待处理预警</span>
          </div>
        )}
        {events.map((event) => (
          <button
            type="button"
            key={event.id}
            className={`psa-notify-item ${severityTone(event.severity)}`}
            onClick={gotoAlerts}
          >
            <span className="title">{event.topic_title || event.rule_name || `事件 #${event.id}`}</span>
            <span className="meta">
              <span>{event.severity} · {event.rule_name || '未知规则'}</span>
              <span>{formatDateTime(event.triggered_at)}</span>
            </span>
          </button>
        ))}
      </div>
      <Button block size="small" onClick={gotoAlerts}>
        进入预警中心
      </Button>
    </div>
  );

  return (
    <Popover
      content={panel}
      trigger="click"
      open={open}
      onOpenChange={setOpen}
      placement="bottomRight"
      arrow={false}
      overlayClassName="psa-notify-popover"
    >
      <span>
        <Badge count={summary?.pending_count ?? 0} size="small" offset={[-6, 6]}>
          <Button className="psa-icon-action" icon={<BellOutlined />} aria-label="预警通知" />
        </Badge>
      </span>
    </Popover>
  );
};
