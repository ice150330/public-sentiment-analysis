import React, { useMemo, useState } from 'react';
import { Alert, Button, Form, Input, Segmented } from 'antd';
import {
  LockOutlined,
  LoginOutlined,
  MailOutlined,
  RadarChartOutlined,
  UserAddOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { confirmPasswordReset, getErrorMessage, requestPasswordReset } from '../../services/api';

type AuthMode = 'login' | 'register' | 'reset';

const modeCopy: Record<AuthMode, { title: string; subtitle: string }> = {
  login: { title: '欢迎回来', subtitle: '登录后进入实时舆情工作台' },
  register: { title: '创建账号', subtitle: '注册即可访问热榜与分析能力' },
  reset: { title: '重置密码', subtitle: '使用一次性令牌重置账号密码' },
};

const Login: React.FC<{ mode?: AuthMode }> = ({ mode = 'login' }) => {
  const [activeMode, setActiveMode] = useState<AuthMode>(mode);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resetToken, setResetToken] = useState<string | null>(null);
  const { user, login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const targetPath = useMemo(() => {
    const state = location.state as { from?: { pathname?: string } } | null;
    return state?.from?.pathname || '/';
  }, [location.state]);

  if (user) {
    return <Navigate to={targetPath} replace />;
  }

  const handleFinish = async (values: { username: string; password?: string; email?: string; token?: string }) => {
    try {
      setSubmitting(true);
      setError(null);
      if (activeMode === 'login') {
        await login(values.username, values.password || '');
        navigate(targetPath, { replace: true });
        return;
      }
      if (activeMode === 'register') {
        await register(values.username, values.password || '', values.email);
        navigate(targetPath, { replace: true });
        return;
      }

      if (!resetToken && !values.token) {
        const response = await requestPasswordReset({ username: values.username });
        setResetToken(response.data.reset_token || null);
        return;
      }

      await confirmPasswordReset({
        token: values.token || resetToken || '',
        new_password: values.password || '',
      });
      setResetToken(null);
      setActiveMode('login');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const copy = modeCopy[activeMode];

  return (
    <main className="psa-auth-screen">
      <section className="psa-auth-shell">
        <div className="psa-auth-hero">
          <div className="psa-auth-hero-mark">
            <RadarChartOutlined />
          </div>
          <div>
            <h1>公众情绪智能分析系统</h1>
            <p>覆盖微博、抖音、头条、百度、B 站、知乎的实时舆情监测、情感研判与预警处置工作台。</p>
          </div>
          <ul className="psa-auth-features">
            <li>
              <span className="dot" />
              <div>
                <strong>多平台热榜聚合</strong>
                <p>六大平台热榜分钟级采集、去重与归一化</p>
              </div>
            </li>
            <li>
              <span className="dot" />
              <div>
                <strong>双模型情感引擎</strong>
                <p>快速 / 增强双模型对比分析，支持批量与低置信复核</p>
              </div>
            </li>
            <li>
              <span className="dot" />
              <div>
                <strong>规则化预警处置</strong>
                <p>P1–P4 分级规则引擎，实时推送与闭环处置</p>
              </div>
            </li>
          </ul>
          <div className="psa-auth-metrics">
            <div>
              <span className="value">6</span>
              <span className="label">监测平台</span>
            </div>
            <div>
              <span className="value">P1–P4</span>
              <span className="label">预警分级</span>
            </div>
            <div>
              <span className="value">2</span>
              <span className="label">情感模型</span>
            </div>
          </div>
        </div>

        <div className="psa-auth-panel">
          <div className="psa-auth-panel-head">
            <h2>{copy.title}</h2>
            <p>{copy.subtitle}</p>
          </div>
          <Segmented
            block
            value={activeMode}
            onChange={(value) => {
              setActiveMode(value as AuthMode);
              setError(null);
              setResetToken(null);
            }}
            options={[
              { value: 'login', label: '登录', icon: <LoginOutlined /> },
              { value: 'register', label: '注册', icon: <UserAddOutlined /> },
              { value: 'reset', label: '重置', icon: <LockOutlined /> },
            ]}
          />
          {error && <Alert type="error" showIcon message={error} />}
          {resetToken && (
            <Alert
              type="success"
              showIcon
              message="重置令牌已生成"
              description={<span className="psa-reset-token">{resetToken}</span>}
            />
          )}
          <Form layout="vertical" onFinish={handleFinish} requiredMark={false}>
            <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
              <Input prefix={<UserOutlined />} autoComplete="username" placeholder="username" />
            </Form.Item>
            {activeMode === 'register' && (
              <Form.Item name="email" label="邮箱">
                <Input prefix={<MailOutlined />} autoComplete="email" placeholder="name@example.com" />
              </Form.Item>
            )}
            {activeMode === 'reset' && resetToken && (
              <Form.Item name="token" label="重置令牌">
                <Input prefix={<LockOutlined />} placeholder="先提交用户名获取令牌" />
              </Form.Item>
            )}
            {(activeMode !== 'reset' || resetToken) && (
              <Form.Item
                name="password"
                label={activeMode === 'reset' ? '新密码' : '密码'}
                rules={[
                  { required: true, message: '请输入密码' },
                  { min: activeMode === 'login' ? 1 : 8, message: '密码至少 8 位' },
                ]}
              >
                <Input.Password prefix={<LockOutlined />} autoComplete={activeMode === 'login' ? 'current-password' : 'new-password'} />
              </Form.Item>
            )}
            <Button
              block
              type="primary"
              htmlType="submit"
              icon={activeMode === 'reset' ? <LockOutlined /> : activeMode === 'login' ? <LoginOutlined /> : <UserAddOutlined />}
              loading={submitting}
            >
              {activeMode === 'reset' ? (resetToken ? '确认重置' : '获取令牌') : activeMode === 'login' ? '登录' : '注册'}
            </Button>
          </Form>
        </div>
      </section>
    </main>
  );
};

export default Login;
