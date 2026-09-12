import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Brain, Upload, Activity, History } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import UploadWizard from './pages/UploadWizard';
import JobTracker from './pages/JobTracker';

// Navigation layout wrapper
const Layout = ({ children }: { children: React.ReactNode }) => {
  const location = useLocation();
  
  const navItems = [
    { path: '/', label: 'Dashboard', icon: <Activity size={20} /> },
    { path: '/generate', label: 'Generate', icon: <Upload size={20} /> },
    { path: '/history', label: 'History', icon: <History size={20} /> }
  ];
  
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <header className="glass-panel" style={{ 
        margin: '1rem', 
        padding: '1rem 2rem', 
        display: 'flex', 
        justifyContent: 'space-between',
        alignItems: 'center',
        borderRadius: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ 
            background: 'linear-gradient(135deg, var(--primary-color), var(--accent-color))',
            padding: '0.5rem',
            borderRadius: '8px',
            color: '#000'
          }}>
            <Brain size={24} />
          </div>
          <h1 style={{ margin: 0, fontSize: '1.5rem' }} className="text-gradient">
            Synthetix AI
          </h1>
        </div>
        
        <nav style={{ display: 'flex', gap: '1.5rem' }}>
          {navItems.map(item => (
            <Link 
              key={item.path} 
              to={item.path}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                color: location.pathname === item.path ? 'var(--primary-color)' : 'var(--text-color)',
                fontWeight: location.pathname === item.path ? 600 : 400
              }}
            >
              {item.icon}
              {item.label}
            </Link>
          ))}
        </nav>
      </header>
      
      <main className="page-container" style={{ flex: 1, width: '100%' }}>
        {children}
      </main>
    </div>
  );
};

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/generate" element={<UploadWizard />} />
          <Route path="/jobs/:jobId" element={<JobTracker />} />
          <Route path="/history" element={<div className="glass-panel"><h2>History</h2><p>Coming soon...</p></div>} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
