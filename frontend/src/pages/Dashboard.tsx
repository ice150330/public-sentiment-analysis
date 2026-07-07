import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Spin, Alert } from 'antd';
import {
  FireOutlined,
  SmileOutlined,
  FrownOutlined,
  MehOutlined,
  CloudServerOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { getDashboardStats, getSentimentDistribution } from '../services/api';

interface DashboardStats {
  total_topics: number;
  today_topics: number;
  active_platforms: number;
  recent_crawls: number;
  total_sentiment_analyzed: number;
}

interface SentimentData {
  labels: string[];
  counts: number[];
  percentages: number[];
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [sentimentData, setSentimentData] = useState<SentimentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statsRes, sentimentRes] = await Promise.all([
        getDashboardStats(),
        getSentimentDistribution(),
      ]);

      setStats(statsRes.data);
      setSentimentData(sentimentRes.data);
      setError(null);
    } catch (err: any) {
      console.error('Failed to fetch dashboard data:', err);
      setError('数据加载失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  // 情感分布饼图配置
  const pieOption = sentimentData
    ? {
        title: {
          text: '情感分布',
          left: 'center',
        },
        tooltip: {
          trigger: 'item',
          formatter: '{a} <br/>{b}: {c} ({d}%)',
        },
        legend: {
          orient: 'vertical',
          left: 'left',
          data: sentimentData.labels,
        },
        series: [
          {
            name: '情感分布',
            type: 'pie',
            radius: ['40%', '70%'],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 10,
              borderColor: '#fff',
              borderWidth: 2,
            },
            label: {
              show: true,
              formatter: '{b}: {d}%',
            },
            emphasis: {
              label: {
                show: true,
                fontSize: 20,
                fontWeight: 'bold',
              },
            },
            data: sentimentData.labels.map((label, index) => ({
              name: label,
              value: sentimentData.counts[index],
            })),
          },
        ],
        color: ['#52c41a', '#faad14', '#f5222d'], // green, yellow, red
      }
    : {};

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <p>加载中...</p>
      </div>
    );
  }

  if (error) {
    return <Alert message="错误" description={error} type="error" showIcon />;
  }

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>数据总览</h1>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={4}>
          <Card>
            <Statistic
              title="总热榜数"
              value={stats?.total_topics || 0}
              prefix={<FireOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="今日热榜"
              value={stats?.today_topics || 0}
              prefix={<FireOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="活跃平台"
              value={stats?.active_platforms || 0}
              prefix={<CloudServerOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="已分析情感"
              value={stats?.total_sentiment_analyzed || 0}
              prefix={<SmileOutlined />}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="正面情感"
              value={
                sentimentData?.counts[
                  sentimentData.labels.indexOf('positive')
                ] || 0
              }
              prefix={<SmileOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card>
            <Statistic
              title="负面情感"
              value={
                sentimentData?.counts[
                  sentimentData.labels.indexOf('negative')
                ] || 0
              }
              prefix={<FrownOutlined style={{ color: '#f5222d' }} />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 图表区域 */}
      <Row gutter={16}>
        <Col span={12}>
          <Card title="情感分布">
            {sentimentData ? (
              <ReactECharts
                option={pieOption}
                style={{ height: 300 }}
              />
            ) : (
              <div>暂无数据</div>
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="平台概览">
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <p>平台数据加载中...</p>
              <p style={{ color: '#999' }}>
                使用爬虫控制页面获取最新数据
              </p>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
