import React from 'react';
import { Link } from 'react-router-dom';

export const Footer: React.FC = () => {
  return (
    <footer style={{ borderTop: '1px solid var(--border-subtle)', backgroundColor: 'var(--bg-primary)', padding: '4rem 2rem 2rem 2rem' }}>
      <div className="page-container flex justify-between" style={{ padding: 0 }}>
        <div>
          <Link to="/" className="flex items-center gap-2" style={{ textDecoration: 'none', marginBottom: '1rem', display: 'inline-flex' }}>
            <img src="/logo.svg" alt="SynthGen" style={{ width: '48px', height: '48px', objectFit: 'contain' }} />
            <span style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-primary)' }}>SynthGen</span>
          </Link>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', maxWidth: '300px' }}>
            AI-Powered Synthetic Data Generation. Create realistic, privacy-safe datasets in seconds.
          </p>
        </div>
        
        <div className="flex gap-6" style={{ gap: '4rem' }}>
          <div className="flex flex-col gap-2">
            <h4 style={{ fontSize: '0.875rem', color: 'var(--text-primary)', marginBottom: '0.5rem', fontWeight: 600 }}>Product</h4>
            <FooterLink to="/features">Features</FooterLink>
            <FooterLink to="/pricing">Pricing</FooterLink>
            <FooterLink to="/docs">Docs</FooterLink>
          </div>
          <div className="flex flex-col gap-2">
            <h4 style={{ fontSize: '0.875rem', color: 'var(--text-primary)', marginBottom: '0.5rem', fontWeight: 600 }}>Resources</h4>
            <FooterLink to="/api">API</FooterLink>
            <FooterLink to="/examples">Examples</FooterLink>
            <FooterLink to="/blog">Blog</FooterLink>
          </div>
          <div className="flex flex-col gap-2">
            <h4 style={{ fontSize: '0.875rem', color: 'var(--text-primary)', marginBottom: '0.5rem', fontWeight: 600 }}>Legal</h4>
            <FooterLink to="/privacy">Privacy</FooterLink>
            <FooterLink to="/terms">Terms</FooterLink>
          </div>
        </div>
      </div>
      <div className="page-container" style={{ padding: '2rem 0 0 0', marginTop: '4rem', borderTop: '1px solid var(--border-subtle)', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
          &copy; {new Date().getFullYear()} SynthGen AI. All rights reserved.
        </p>
      </div>
    </footer>
  );
};

const FooterLink: React.FC<{ to: string; children: React.ReactNode }> = ({ to, children }) => (
  <Link to={to} style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', textDecoration: 'none' }}>
    {children}
  </Link>
);
