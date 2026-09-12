import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Lock, Mail, ArrowRight, Loader } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { API_BASE } from '../lib/api';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const res = await axios.post(`${API_BASE}/v1/auth/login`, formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });

      login(res.data.access_token);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel"
      style={{ maxWidth: '400px', margin: '4rem auto', padding: '2.5rem' }}
    >
      <h2 style={{ textAlign: 'center', marginBottom: '0.5rem' }}>Welcome Back</h2>
      <p style={{ textAlign: 'center', color: 'var(--text-color)', marginBottom: '2rem', fontSize: '0.9rem' }}>
        Log in to manage your synthetic datasets
      </p>

      <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div style={{ position: 'relative' }}>
          <Mail size={20} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-color)', opacity: 0.7 }} />
          <input
            type="email"
            placeholder="Email Address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{
              width: '100%',
              padding: '12px 12px 12px 40px',
              borderRadius: '8px',
              border: '1px solid var(--glass-border)',
              background: 'rgba(255, 255, 255, 0.05)',
              color: '#fff',
              fontSize: '1rem',
              boxSizing: 'border-box'
            }}
          />
        </div>

        <div style={{ position: 'relative' }}>
          <Lock size={20} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-color)', opacity: 0.7 }} />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{
              width: '100%',
              padding: '12px 12px 12px 40px',
              borderRadius: '8px',
              border: '1px solid var(--glass-border)',
              background: 'rgba(255, 255, 255, 0.05)',
              color: '#fff',
              fontSize: '1rem',
              boxSizing: 'border-box'
            }}
          />
        </div>

        {error && (
          <div style={{ color: 'var(--danger-color)', fontSize: '0.85rem', textAlign: 'center' }}>
            {error}
          </div>
        )}

        <button type="submit" className="btn-primary" disabled={isLoading} style={{ width: '100%', justifyContent: 'center' }}>
          {isLoading ? <Loader className="spin" size={20} /> : <>Log In <ArrowRight size={20} /></>}
        </button>
      </form>

      <p style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.9rem', color: 'var(--text-color)' }}>
        Don't have an account? <Link to="/register" style={{ color: 'var(--primary-color)', textDecoration: 'none', fontWeight: 600 }}>Sign up</Link>
      </p>
    </motion.div>
  );
};

export default Login;
