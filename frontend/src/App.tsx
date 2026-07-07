import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from 'antd';
import Dashboard from './pages/Dashboard';
import Topics from './pages/Topics';
import Sentiment from './pages/Sentiment';
import Stats from './pages/Stats';
import Navbar from './components/Navbar';
import './index.css';

const { Header, Content, Footer } = Layout;

const App: React.FC = () => {
  return (
    <Router>
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{ background: '#001529', padding: 0 }}>
          <Navbar />
        </Header>
        <Content style={{ padding: '24px', background: '#f0f2f5' }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/topics" element={<Topics />} />
            <Route path="/sentiment" element={<Sentiment />} />
            <Route path="/stats" element={<Stats />} />
          </Routes>
        </Content>
        <Footer style={{ textAlign: 'center', background: '#001529', color: '#fff' }}>
          公众情绪智能分析系统 ©2026 毕业设计
        </Footer>
      </Layout>
    </Router>
  );
};

export default App;