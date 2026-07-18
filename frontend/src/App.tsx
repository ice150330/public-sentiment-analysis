import React from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { AuthProvider, useAuth } from './auth/AuthContext';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Profile from './pages/Profile';
import Topics from './pages/Topics';
import Sentiment from './pages/Sentiment';
import Stats from './pages/Stats';
import { RealtimeNotifier } from './components/RealtimeNotifier';
import './index.css';

const roleLevel = {
  visitor: 1,
  analyst: 2,
  admin: 3,
};

const ProtectedRoute: React.FC<{ children: React.ReactElement; minRole?: keyof typeof roleLevel }> = ({ children, minRole = 'visitor' }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <main className="psa-auth-screen">
        <Spin size="large" />
      </main>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (roleLevel[user.role] < roleLevel[minRole]) {
    return <Navigate to="/" replace />;
  }

  return children;
};

const App: React.FC = () => {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login mode="login" />} />
          <Route path="/register" element={<Login mode="register" />} />
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/topics" element={<ProtectedRoute><Topics /></ProtectedRoute>} />
          <Route path="/analysis" element={<ProtectedRoute><Sentiment /></ProtectedRoute>} />
          <Route path="/sentiment" element={<Navigate to="/analysis" replace />} />
          <Route path="/management" element={<ProtectedRoute minRole="admin"><Stats /></ProtectedRoute>} />
          <Route path="/stats" element={<Navigate to="/management" replace />} />
          <Route path="/monitor" element={<ProtectedRoute><Dashboard initialView="visual" /></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <RealtimeNotifier />
      </AuthProvider>
    </Router>
  );
};

export default App;
