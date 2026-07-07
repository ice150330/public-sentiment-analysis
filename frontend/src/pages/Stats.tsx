import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Select, DatePicker, Spin, Alert } from 'antd';
import ReactECharts from 'echarts-for-react';
import {
  getHeatRanking,
  getCategoryDistribution,
  getPlatformComparison,
  getCrawlStats,
  getPlatforms,
} from '../services/api';

const { RangePicker } = DatePicker;

interface Platform {
  id: number;
  name: string;
  display_name: string;
}

const Stats: React.FC = () => {
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [selectedPlatform, setSelectedPlatform] = useState<number | undefined>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [heatRanking, setHeatRanking] = useState<any[]>([]);
  const [categoryData, setCategoryData] = useState<any>(null);
  const [platformComparison, setPlatformComparison] = useState<any>(null);
  const [crawlStats, setCrawlStats] = useState<any>(null);

  useEffect(() => {
    fetchPlatforms();
    fetchAllStats();
  }, []);

  useEffect(() => {
    fetchAllStats();
  }, [selectedPlatform]);

  const fetchPlatforms = async () => {
    try {
      const res = await getPlatforms();
      setPlatforms(res.data || []);
    } catch (err) {
      console.error('Failed to fetch platforms:', err);
    }
  };

  const fetchAllStats = async () => {
    try {
      setLoading(true);
      setError(null);

      const params: any = {};
      if (selectedPlatform) params.platform_id = selectedPlatform;

      const [heatRes, categoryRes, comparisonRes, crawlRes] = await Promise.all([
        getHeatRanking({ ...params, limit: 10 }),
        getCategoryDistribution(params),
        getPlatformComparison(params),
        getCrawlStats(params),
      ]);

      setHeatRanking(heatRes.data || []);
      setCategoryData(categoryRes.data);
      setPlatformComparison(comparisonRes.data);
      setCrawlStats(crawlRes.data);
    } catch (err: any) {
      console.error('Failed to fetch stats:', err);
      setError('统计数据加载失败');
    } finally {
      setLoading(false);
    }
  };

  // 热度排行图表
  const heatRankingOption = {
    title: { text: '热度排行 Top 10', left: 'center' },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: heatRanking.map((item) => item.topic),
      axisLabel: { rotate: 45 },
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: '热度',
        type: 'bar',
        data: heatRanking.map((item) => item.heat_score),
        itemStyle: { color: '#1890ff' },
      },
    ],
  };

  // 分类分布图表
  const categoryOption = categoryData
    ? {
        title: { text: '分类分布', left: 'center' },
        tooltip: { trigger: 'item' },
        series: [
          {
            name: '分类',
            type: 'pie',
            radius: '50%',
            data: categoryData.labels?.map((label: string, index: number) => ({
              name: label,
              value: categoryData.counts[index],
            })) || [],
          },
        ],
      }
    : {};

  // 平台对比图表
  const platformOption = platformComparison
    ? {
        title: { text: '平台对比', left: 'center' },
        tooltip: { trigger: 'axis' },
        legend: { data: ['热度', '话题数'] },
        xAxis: {
          type: 'category',
          data: platformComparison.map((p: any) => p.platform),
        },
        yAxis: [
          { type: 'value', name: '热度' },
          { type: 'value', name: '话题数' },
        ],
        series: [
          {
            name: '热度',
            type: 'bar',
            data: platformComparison.map((p: any) => p.avg_heat),
          },
          {
            name: '话题数',
            type: 'line',
            yAxisIndex: 1,
            data: platformComparison.map((p: any) => p.topic_count),
          },
        ],
      }
    : {};

  // 爬虫统计图表
  const crawlOption = crawlStats
    ? {
        title: { text: '爬虫采集统计', left: 'center' },
        tooltip: { trigger: 'axis' },
        xAxis: {
          type: 'category',
          data: crawlStats.map((s: any) => s.date),
        },
        yAxis: { type: 'value' },
        series: [
          {
            name: '采集数',
            type: 'line',
            data: crawlStats.map((s: any) => s.count),
            smooth: true,
          },
        ],
      }
    : {};

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>统计分析</h1>

      <Card style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 16 }}>
          <Select
            placeholder="选择平台"
            allowClear
            style={{ width: 200 }}
            value={selectedPlatform}
            onChange={(value) => setSelectedPlatform(value)}
            options={platforms.map((p) => ({
              value: p.id,
              label: p.display_name,
            }))}
          />
          <button onClick={fetchAllStats}>刷新</button>
        </div>
      </Card>

      {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 16 }} />}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Spin size="large" />
          <p>加载中...</p>
        </div>
      ) : (
        <Row gutter={16}>
          <Col span={12} style={{ marginBottom: 16 }}>
            <Card title="热度排行">
              <ReactECharts option={heatRankingOption} style={{ height: 300 }} />
            </Card>
          </Col>
          <Col span={12} style={{ marginBottom: 16 }}>
            <Card title="分类分布">
              <ReactECharts option={categoryOption} style={{ height: 300 }} />
            </Card>
          </Col>
          <Col span={12} style={{ marginBottom: 16 }}>
            <Card title="平台对比">
              <ReactECharts option={platformOption} style={{ height: 300 }} />
            </Card>
          </Col>
          <Col span={12} style={{ marginBottom: 16 }}>
            <Card title="爬虫统计">
              <ReactECharts option={crawlOption} style={{ height: 300 }} />
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
};

export default Stats;
