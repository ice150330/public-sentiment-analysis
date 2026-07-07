import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Input, DatePicker, Select, Spin, Alert } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { getTopics, getPlatforms, searchTopics } from '../services/api';

const { RangePicker } = DatePicker;

interface Topic {
  id: number;
  title: string;
  content_summary: string;
  heat_score: number;
  platform: string;
  category: string;
  crawl_time: string;
}

interface Platform {
  id: number;
  name: string;
  display_name: string;
}

const Topics: React.FC = () => {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState<number | undefined>();
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);

  useEffect(() => {
    fetchPlatforms();
    fetchTopics();
  }, []);

  const fetchPlatforms = async () => {
    try {
      const res = await getPlatforms();
      setPlatforms(res.data || []);
    } catch (err) {
      console.error('Failed to fetch platforms:', err);
    }
  };

  const fetchTopics = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (selectedPlatform) params.platform_id = selectedPlatform;
      if (dateRange) {
        params.start_time = dateRange[0].format('YYYY-MM-DD HH:mm:ss');
        params.end_time = dateRange[1].format('YYYY-MM-DD HH:mm:ss');
      }
      params.limit = 50;

      const res = await getTopics(params);
      setTopics(res.data || []);
      setError(null);
    } catch (err: any) {
      console.error('Failed to fetch topics:', err);
      setError('加载热榜数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchKeyword.trim()) {
      fetchTopics();
      return;
    }
    try {
      setLoading(true);
      const res = await searchTopics(searchKeyword);
      setTopics(res.data || []);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: '平台',
      dataIndex: 'platform',
      key: 'platform',
      render: (platform: string) => <Tag color="blue">{platform}</Tag>,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
    },
    {
      title: '热度',
      dataIndex: 'heat_score',
      key: 'heat_score',
      render: (score: number) => <Tag color="red">{score}</Tag>,
    },
    {
      title: '采集时间',
      dataIndex: 'crawl_time',
      key: 'crawl_time',
    },
  ];

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>热榜数据</h1>

      <Card style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 16 }}>
          <Input
            placeholder="搜索关键词"
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            onPressEnter={handleSearch}
            prefix={<SearchOutlined />}
            style={{ width: 300 }}
          />
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
          <RangePicker
            showTime
            value={dateRange}
            onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
          />
          <button onClick={fetchTopics}>刷新</button>
        </div>
      </Card>

      {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 16 }} />}

      <Table
        columns={columns}
        dataSource={topics}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />
    </div>
  );
};

export default Topics;
