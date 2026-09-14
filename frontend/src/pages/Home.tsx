import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Shield, Zap, Layers } from 'lucide-react';
import { Navbar } from '../components/layout/Navbar';
import { Footer } from '../components/layout/Footer';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';

const Home: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      
      <main className="flex-1 w-full" style={{ paddingTop: '80px' }}>
        {/* Hero Section */}
        <section className="flex flex-col items-center justify-center text-center px-4" style={{ padding: '8rem 0 6rem 0' }}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="flex flex-col items-center max-w-4xl mx-auto gap-6"
          >
            <div className="badge badge-outline mb-4">Synthetix AI 2.0 is now live</div>
            <h1 style={{ fontSize: '4rem', marginBottom: '1rem' }} className="text-gradient">
              Generate Synthetic Data.<br />Ship Faster.
            </h1>
            <p style={{ fontSize: '1.25rem', color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto 2rem auto' }}>
              Create realistic, privacy-safe datasets for development, testing, analytics, and machine learning in seconds.
            </p>
            
            <div className="flex gap-4">
              <Button size="lg" onClick={() => navigate('/app/dashboard')}>
                Start Generating <ArrowRight size={18} className="ml-2" />
              </Button>
              <Button variant="secondary" size="lg" onClick={() => navigate('/pricing')}>
                Explore Features
              </Button>
            </div>
          </motion.div>
        </section>

        {/* Product Preview Section */}
        <section className="page-container" style={{ paddingBottom: '6rem' }}>
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <div className="glass-panel" style={{ padding: 0, overflow: 'hidden', border: '1px solid var(--border-strong)', borderRadius: 'var(--radius-xl)' }}>
              {/* Mock UI Header */}
              <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-subtle)', backgroundColor: 'var(--bg-secondary)', display: 'flex', gap: '0.5rem' }}>
                <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#ef4444' }} />
                <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#f59e0b' }} />
                <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#10b981' }} />
              </div>
              
              {/* Mock UI Body */}
              <div style={{ padding: '3rem', backgroundColor: 'var(--bg-tertiary)' }} className="flex flex-col gap-6">
                <div className="flex justify-between items-center">
                  <h3 style={{ margin: 0 }}>Configure Dataset</h3>
                  <Button size="sm">Generate 10,000 Rows</Button>
                </div>
                
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
                  {[
                    { col: 'id', type: 'UUID' },
                    { col: 'email', type: 'Email Address' },
                    { col: 'full_name', type: 'Full Name' },
                    { col: 'purchase_amount', type: 'Float' },
                    { col: 'created_at', type: 'DateTime' }
                  ].map((field, i) => (
                    <Card key={i} className="flex flex-col gap-1 p-3">
                      <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>{field.col}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{field.type}</span>
                    </Card>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        </section>

        {/* Features Section */}
        <section className="page-container" style={{ paddingBottom: '8rem' }}>
          <div className="text-center mb-12">
            <h2>Everything you need for data</h2>
            <p style={{ color: 'var(--text-secondary)' }}>Powerful tools designed for modern engineering teams.</p>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
            <FeatureCard 
              icon={<Layers />} 
              title="Custom Schemas" 
              desc="Define exactly what your dataset should contain with our powerful schema builder." 
            />
            <FeatureCard 
              icon={<Zap />} 
              title="Instant Generation" 
              desc="Generate thousands of rows in seconds using our highly optimized generation engine." 
            />
            <FeatureCard 
              icon={<Shield />} 
              title="Privacy-Friendly" 
              desc="Never use real user data in testing again. Fully compliant synthetic alternatives." 
            />
          </div>
        </section>

      </main>

      <Footer />
    </div>
  );
};

const FeatureCard: React.FC<{ icon: React.ReactNode; title: string; desc: string }> = ({ icon, title, desc }) => (
  <Card>
    <div style={{ padding: '2rem' }} className="flex flex-col gap-4">
      <div style={{ width: '48px', height: '48px', borderRadius: '12px', backgroundColor: 'var(--bg-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-primary)' }}>
        {icon}
      </div>
      <h3 style={{ fontSize: '1.25rem', margin: 0 }}>{title}</h3>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>{desc}</p>
    </div>
  </Card>
);

export default Home;
