import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { Brain, Upload, Activity, History as HistoryIcon, LogOut, User as UserIcon, Settings } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import UploadWizard from './pages/UploadWizard';
import JobTracker from './pages/JobTracker';
import Login from './pages/Login';
import Register from './pages/Register';
import Home from './pages/Home';
import History from './pages/History';
import Profile from './pages/Profile';
import Verify from './pages/Verify';
import { AuthProvider, useAuth } from './context/AuthContext';

// Navigation layout wrapper
const Layout = ({ children }: { children: React.ReactNode }) => {
  const location = useLocation();
  const { user, logout } = useAuth();
  
  // Hide nav on auth pages and home page
  const isAuthPage = ['/login', '/register', '/verify'].includes(location.pathname);
  const isHomePage = location.pathname === '/';
  
  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: <Activity size={20} /> },
    { path: '/generate', label: 'Generate', icon: <Upload size={20} /> },
    { path: '/history', label: 'History', icon: <HistoryIcon size={20} /> }
  ];
  
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {!isAuthPage && !isHomePage && (
        <header className="glass-panel" style={{ 
          margin: '1rem', 
          padding: '1rem 2rem', 
          display: 'flex', 
          justifyContent: 'space-between',
          alignItems: 'center',
          borderRadius: '12px'
        }}>
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', textDecoration: 'none' }}>
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
          </Link>
          
          <nav style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
            {navItems.map(item => (
              <Link 
                key={item.path} 
                to={item.path}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  color: location.pathname.startsWith(item.path) ? 'var(--primary-color)' : 'var(--text-color)',
                  fontWeight: location.pathname.startsWith(item.path) ? 600 : 400,
                  textDecoration: 'none'
                }}
              >
                {item.icon}
                {item.label}
              </Link>
            ))}
            
            {user && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginLeft: '1rem', paddingLeft: '1rem', borderLeft: '1px solid rgba(255,255,255,0.1)' }}>
                <Link to="/profile" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: location.pathname === '/profile' ? 'var(--primary-color)' : 'var(--text-color)', textDecoration: 'none', fontSize: '0.9rem' }}>
                  <UserIcon size={16} />
                  {user.email.split('@')[0]}
                </Link>
                <button onClick={logout} style={{ background: 'none', border: 'none', color: 'var(--danger-color)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.9rem' }}>
                  <LogOut size={16} />
                </button>
              </div>
            )}
          </nav>
        </header>
      )}
      
      {/* Small Header for Home Page */}
      {isHomePage && (
        <header className="absolute top-0 w-full p-6 flex justify-between items-center z-10">
          <div className="flex items-center gap-2">
            <Brain size={28} className="text-[var(--primary-color)]" />
            <h1 className="text-2xl font-bold tracking-tight">Synthetix AI</h1>
          </div>
          <div className="flex gap-4 items-center">
            {user ? (
               <Link to="/dashboard" className="text-gray-300 hover:text-white font-medium">Dashboard</Link>
            ) : (
              <>
                <Link to="/login" className="text-gray-300 hover:text-white font-medium">Login</Link>
                <Link to="/register" className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors font-medium">Sign Up</Link>
              </>
            )}
          </div>
        </header>
      )}

      <main className="page-container" style={{ flex: 1, width: '100%' }}>
        {children}
      </main>
    </div>
  );
};

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, isLoading } = useAuth();
  
  if (isLoading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>Loading...</div>;
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/verify" element={<Verify />} />
            
            {/* Protected Routes */}
            <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/generate" element={<ProtectedRoute><UploadWizard /></ProtectedRoute>} />
            <Route path="/jobs/:jobId" element={<ProtectedRoute><JobTracker /></ProtectedRoute>} />
            <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
            <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
