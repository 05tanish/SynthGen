import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Brain, Zap, Shield, Database, ChevronRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Home() {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <div className="flex-1 flex flex-col items-center justify-center text-center p-8 mt-12">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 mb-8 animate-fade-in">
          <Brain size={18} className="text-[var(--primary-color)]" />
          <span className="text-sm font-medium">Agentic AI Synthetic Data Generation</span>
        </div>
        
        <h1 className="text-5xl md:text-7xl font-bold mb-6 max-w-4xl leading-tight">
          Generate <span className="text-gradient">Production-Grade</span> Data in Seconds
        </h1>
        
        <p className="text-xl text-gray-400 mb-10 max-w-2xl">
          Stop waiting for data access approvals. Use our intelligent AI agents to instantly generate high-quality, privacy-safe synthetic datasets tailored exactly to your schema and relationships.
        </p>
        
        <div className="flex gap-4">
          {user ? (
            <button 
              onClick={() => navigate('/dashboard')}
              className="px-8 py-4 bg-[var(--primary-color)] text-black rounded-lg font-bold text-lg hover:bg-[var(--accent-color)] transition-colors flex items-center gap-2 shadow-[0_0_20px_rgba(20,241,149,0.3)]"
            >
              Go to Dashboard
              <ChevronRight size={20} />
            </button>
          ) : (
            <>
              <button 
                onClick={() => navigate('/register')}
                className="px-8 py-4 bg-[var(--primary-color)] text-black rounded-lg font-bold text-lg hover:bg-[var(--accent-color)] transition-colors flex items-center gap-2 shadow-[0_0_20px_rgba(20,241,149,0.3)]"
              >
                Get Started
                <ChevronRight size={20} />
              </button>
              <button 
                onClick={() => navigate('/login')}
                className="px-8 py-4 bg-white/5 border border-white/10 rounded-lg font-bold text-lg hover:bg-white/10 transition-colors"
              >
                Login
              </button>
            </>
          )}
        </div>
      </div>

      {/* Features Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 p-8 max-w-6xl mx-auto mb-20">
        <div className="glass-panel p-8 text-center flex flex-col items-center hover:-translate-y-2 transition-transform duration-300">
          <div className="w-16 h-16 rounded-full bg-blue-500/10 flex items-center justify-center mb-6 text-blue-400">
            <Zap size={32} />
          </div>
          <h3 className="text-xl font-bold mb-4">Instant Generation</h3>
          <p className="text-gray-400">Our Agentic AI orchestrates complex deep learning models like CTGAN to generate data instantly.</p>
        </div>
        
        <div className="glass-panel p-8 text-center flex flex-col items-center hover:-translate-y-2 transition-transform duration-300 border border-[var(--primary-color)]/20">
          <div className="w-16 h-16 rounded-full bg-[var(--primary-color)]/10 flex items-center justify-center mb-6 text-[var(--primary-color)]">
            <Shield size={32} />
          </div>
          <h3 className="text-xl font-bold mb-4">Privacy Preserving</h3>
          <p className="text-gray-400">Never expose PII again. Generate synthetic data that mirrors your statistical distributions exactly without leaking secrets.</p>
        </div>
        
        <div className="glass-panel p-8 text-center flex flex-col items-center hover:-translate-y-2 transition-transform duration-300">
          <div className="w-16 h-16 rounded-full bg-purple-500/10 flex items-center justify-center mb-6 text-purple-400">
            <Database size={32} />
          </div>
          <h3 className="text-xl font-bold mb-4">Relational Integrity</h3>
          <p className="text-gray-400">Our advanced schema analyzers maintain complex cross-column relationships and correlations.</p>
        </div>
      </div>
    </div>
  );
}
