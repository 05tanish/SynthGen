import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Lock, Mail, ArrowRight, Loader } from 'lucide-react';
import { API_BASE } from '../lib/api';
import { useAuth } from '../context/AuthContext';

const Register = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      // Register
      await axios.post(`${API_BASE}/v1/auth/register`, {
        email,
        password
      });

      // Auto login
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
      setError(err.response?.data?.detail || 'Registration failed. Please try again.');
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
      <h2 style={{ textAlign: 'center', marginBottom: '0.5rem' }}>Create Account</h2>
      <p style={{ textAlign: 'center', color: 'var(--text-color)', marginBottom: '2rem', fontSize: '0.9rem' }}>
        Join to start generating synthetic data
      </p>

      <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
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
            minLength={6}
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
          {isLoading ? <Loader className="spin" size={20} /> : <>Sign Up <ArrowRight size={20} /></>}
        </button>
      </form>

      <p style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.9rem', color: 'var(--text-color)' }}>
        Already have an account? <Link to="/login" style={{ color: 'var(--primary-color)', textDecoration: 'none', fontWeight: 600 }}>Log in</Link>
      </p>
    </motion.div>
  );
};

export default Register;
