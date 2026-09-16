import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Activity, Upload, Database, LayoutTemplate, Settings, Key, BarChart } from 'lucide-react';

export const Sidebar: React.FC = () => {
  const location = useLocation();
  const path = location.pathname;

  return (
    <aside style={{
      width: '240px',
      height: '100vh',
      backgroundColor: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      padding: '1.5rem 1rem',
      position: 'sticky',
      top: 0,
    }}>
      <Link to="/app/dashboard" className="flex items-center gap-2 mb-8 px-2" style={{ textDecoration: 'none' }}>
        <img src="/logo.svg" alt="SynthGen" style={{ width: '40px', height: '40px', objectFit: 'contain' }} />
        <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '1.1rem' }}>SynthGen</span>
      </Link>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', flex: 1 }}>
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.75rem', paddingLeft: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Overview</div>
          <nav className="flex flex-col gap-1">
            <SidebarItem icon={<Activity size={18} />} label="Dashboard" to="/app/dashboard" active={path === '/app/dashboard'} />
          </nav>
        </div>

        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.75rem', paddingLeft: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Workspace</div>
          <nav className="flex flex-col gap-1">
            <SidebarItem icon={<Upload size={18} />} label="Generate" to="/app/generate" active={path.startsWith('/app/generate')} />
            <SidebarItem icon={<Database size={18} />} label="Datasets" to="/app/datasets" active={path.startsWith('/app/datasets') || path.startsWith('/app/history')} />
            <SidebarItem icon={<LayoutTemplate size={18} />} label="Templates" to="/app/templates" active={path.startsWith('/app/templates')} />
          </nav>
        </div>

        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.75rem', paddingLeft: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>API & Usage</div>
          <nav className="flex flex-col gap-1">
            <SidebarItem icon={<Key size={18} />} label="API Keys" to="/app/api-keys" active={path.startsWith('/app/api-keys')} />
            <SidebarItem icon={<BarChart size={18} />} label="Usage" to="/app/usage" active={path.startsWith('/app/usage')} />
          </nav>
        </div>
      </div>

      <div>
        <nav className="flex flex-col gap-1">
          <SidebarItem icon={<Settings size={18} />} label="Settings" to="/app/settings" active={path.startsWith('/app/settings')} />
        </nav>
      </div>
    </aside>
  );
};

const SidebarItem: React.FC<{ icon: React.ReactNode; label: string; to: string; active?: boolean }> = ({ icon, label, to, active }) => {
  return (
    <Link 
      to={to} 
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        padding: '0.5rem',
        borderRadius: 'var(--radius-md)',
        color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
        backgroundColor: active ? 'var(--surface-active)' : 'transparent',
        textDecoration: 'none',
        fontWeight: 500,
        fontSize: '0.875rem',
        transition: 'all 0.2s ease'
      }}
      onMouseEnter={(e) => {
        if (!active) e.currentTarget.style.backgroundColor = 'var(--surface-hover)';
      }}
      onMouseLeave={(e) => {
        if (!active) e.currentTarget.style.backgroundColor = 'transparent';
      }}
    >
      {icon}
      {label}
    </Link>
  );
};
