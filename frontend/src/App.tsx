import React from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Topics from './pages/Topics';
import Sentiment from './pages/Sentiment';
import Stats from './pages/Stats';
import './index.css';

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/topics" element={<Topics />} />
        <Route path="/analysis" element={<Sentiment />} />
        <Route path="/sentiment" element={<Navigate to="/analysis" replace />} />
        <Route path="/management" element={<Stats />} />
        <Route path="/stats" element={<Navigate to="/management" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
};

export default App;
