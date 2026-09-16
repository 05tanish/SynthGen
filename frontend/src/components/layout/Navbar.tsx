import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../ui/Button';

export const Navbar: React.FC = () => {
  return (
    <header className="flex justify-between items-center" style={{ padding: '1.5rem 2rem', position: 'absolute', top: 0, width: '100%', zIndex: 50 }}>
      <Link to="/" className="flex items-center gap-2 text-gradient" style={{ textDecoration: 'none' }}>
        <img src="/logo.svg" alt="SynthGen" style={{ width: '64px', height: '64px', objectFit: 'contain' }} />
        <span style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>SynthGen</span>
      </Link>
      
      <nav className="flex items-center gap-6" style={{ display: 'none' }}>
        {/* We can add media queries later, but for now inline styles mock utility classes */}
        <Link to="/features">Features</Link>
        <Link to="/how-it-works">How it Works</Link>
        <Link to="/pricing">Pricing</Link>
        <Link to="/docs">Docs</Link>
      </nav>

      <div className="flex items-center gap-4">
        <Link to="/login" style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-secondary)' }}>Log in</Link>
        <Link to="/register">
          <Button variant="primary" size="sm">Get Started</Button>
        </Link>
      </div>
    </header>
  );
};
