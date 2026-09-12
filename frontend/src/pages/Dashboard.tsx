
import { Link } from 'react-router-dom';
import { Database, Zap, Shield, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

const Dashboard = () => {
  const features = [
    {
      title: 'Autonomous Generation',
      description: 'Upload your data and our AI orchestrates profiling, relationship extraction, and hyperparameter tuning.',
      icon: <Zap size={32} color="var(--primary-color)" />
    },
    {
      title: 'Privacy Guaranteed',
      description: 'Empirical checks ensure your synthetic data does not memorize original rows (exact match or nearest neighbor).',
      icon: <Shield size={32} color="var(--accent-color)" />
    },
    {
      title: 'High ML Utility',
      description: 'Maintains statistical distributions and correlations so you can train reliable downstream models.',
      icon: <Sparkles size={32} color="var(--success-color)" />
    }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '3rem' }}>
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel" 
        style={{ textAlign: 'center', padding: '4rem 2rem' }}
      >
        <h2 style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>
          Welcome to <span className="text-gradient">Synthetix AI</span>
        </h2>
        <p style={{ fontSize: '1.2rem', color: 'var(--text-color)', maxWidth: '600px', margin: '0 auto 2rem auto' }}>
          Production-quality synthetic data generation. Autonomous, intelligent, and secure.
        </p>
        <Link to="/generate" className="btn-primary" style={{ fontSize: '1.1rem' }}>
          <Database size={20} />
          Start New Generation
        </Link>
      </motion.div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
        {features.map((feature, i) => (
          <motion.div 
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.2 }}
            className="glass-panel"
            style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}
          >
            <div style={{ 
              background: 'rgba(31, 40, 51, 0.5)', 
              padding: '1rem', 
              borderRadius: '50%',
              marginBottom: '1.5rem'
            }}>
              {feature.icon}
            </div>
            <h3>{feature.title}</h3>
            <p style={{ color: 'var(--text-color)' }}>{feature.description}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default Dashboard;
