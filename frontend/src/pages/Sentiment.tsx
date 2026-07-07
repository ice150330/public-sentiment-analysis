import React, { useState } from 'react';
import { Card, Input, Button, Tag, Spin, Alert } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { analyzeText, analyzeBatch } from '../services/api';

interface SentimentResult {
  text: string;
  sentiment_label: string;
  confidence: number;
  scores: {
    positive: number;
    negative: number;
    neutral: number;
  };
}

const Sentiment: React.FC = () => {
  const [text, setText] = useState('');
  const [results, setResults] = useState<SentimentResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    if (!text.trim()) return;

    try {
      setLoading(true);
      setError(null);
      const res = await analyzeText(text);
      setResults([res.data]);
    } catch (err: any) {
      console.error('Analysis failed:', err);
      setError('分析失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleBatchAnalyze = async () => {
    const texts = text.split('\n').filter((t) => t.trim());
    if (texts.length === 0) return;

    try {
      setLoading(true);
      setError(null);
      const res = await analyzeBatch(texts);
      setResults(res.data);
    } catch (err: any) {
      console.error('Batch analysis failed:', err);
      setError('批量分析失败');
    } finally {
      setLoading(false);
    }
  };

  const getSentimentColor = (label: string) => {
    switch (label) {
      case 'positive':
        return 'green';
      case 'negative':
        return 'red';
      default:
        return 'orange';
    }
  };

  const getSentimentText = (label: string) => {
    switch (label) {
      case 'positive':
        return '正面';
      case 'negative':
        return '负面';
      default:
        return '中性';
    }
  };

  // 情感分数图表
  const chartOption = results.length > 0
    ? {
        title: {
          text: '情感分析结果',
          left: 'center',
        },
        tooltip: {
          trigger: 'axis',
        },
        xAxis: {
          type: 'category',
          data: results.map((_, i) => `文本${i + 1}`),
        },
        yAxis: {
          type: 'value',
          max: 1,
        },
        series: [
          {
            name: '正面',
            type: 'bar',
            data: results.map((r) => r.scores.positive),
            itemStyle: { color: '#52c41a' },
          },
          {
            name: '负面',
            type: 'bar',
            data: results.map((r) => r.scores.negative),
            itemStyle: { color: '#f5222d' },
          },
          {
            name: '中性',
            type: 'bar',
            data: results.map((r) => r.scores.neutral),
            itemStyle: { color: '#faad14' },
          },
        ],
      }
    : {};

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>情感分析</h1>

      <Card style={{ marginBottom: 24 }}>
        <div style={{ marginBottom: 16 }}>
          <Input.TextArea
            placeholder="输入要分析的文本（支持多行，每行一条）"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
          />
        </div>
        <div style={{ display: 'flex', gap: 16 }}>
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleAnalyze}
            loading={loading}
          >
            单条分析
          </Button>
          <Button
            icon={<SendOutlined />}
            onClick={handleBatchAnalyze}
            loading={loading}
          >
            批量分析
          </Button>
        </div>
      </Card>

      {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 16 }} />}

      {results.length > 0 && (
        <Card title="分析结果" style={{ marginBottom: 24 }}>
          <div style={{ marginBottom: 24 }}>
            {results.map((result, index) => (
              <div
                key={index}
                style={{
                  marginBottom: 16,
                  padding: 16,
                  border: '1px solid #f0f0f0',
                  borderRadius: 8,
                }}
              >
                <div style={{ marginBottom: 8 }}>
                  <strong>文本:</strong> {result.text}
                </div>
                <div>
                  <strong>情感:</strong>{' '}
                  <Tag color={getSentimentColor(result.sentiment_label)}>
                    {getSentimentText(result.sentiment_label)} ({(result.confidence * 100).toFixed(1)}%)
                  </Tag>
                </div>
                <div style={{ marginTop: 8, color: '#666', fontSize: 12 }}>
                  正面: {(result.scores.positive * 100).toFixed(1)}% | 
                  负面: {(result.scores.negative * 100).toFixed(1)}% | 
                  中性: {(result.scores.neutral * 100).toFixed(1)}%
                </div>
              </div>
            ))}
          </div>

          {results.length > 1 && (
            <ReactECharts
              option={chartOption}
              style={{ height: 300 }}
            />
          )}
        </Card>
      )}
    </div>
  );
};

export default Sentiment;
