import React from 'react';
import { Menu } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  DashboardOutlined,
  FireOutlined,
  SmileOutlined,
  BarChartOutlined,
  MonitorOutlined,
} from '@ant-design/icons';

const Navbar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '总览',
    },
    {
      key: '/topics',
      icon: <FireOutlined />,
      label: '热榜数据',
    },
    {
      key: '/sentiment',
      icon: <SmileOutlined />,
      label: '情感分析',
    },
    {
      key: '/stats',
      icon: <BarChartOutlined />,
      label: '统计分析',
    },
    {
      key: '/monitor',
      icon: <MonitorOutlined />,
      label: '监控面板',
    },
  ];

  return (
    <Menu
      theme="dark"
      mode="horizontal"
      selectedKeys={[location.pathname]}
      items={menuItems}
      onClick={({ key }) => navigate(key)}
      style={{ lineHeight: '64px' }}
    />
  );
};

export default Navbar;
