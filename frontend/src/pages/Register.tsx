import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { GoogleLogin, type CredentialResponse } from '@react-oauth/google';
import { useAuth } from '../context/AuthContext';
import { Card, CardContent } from '../components/ui/Card';
import axios from 'axios';
import { API_BASE } from '../lib/api';

const Register: React.FC = () => {
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    try {
      setIsLoading(true);
      setError('');
      const res = await axios.post(`${API_BASE}/api/v1/auth/google-login`, {
        token: credentialResponse.credential,
      });
      login(res.data.access_token);
      navigate('/app/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Google Sign-up failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      backgroundColor: 'var(--bg-primary)',
      padding: '1rem',
    }}>
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem', textDecoration: 'none' }}>
        <img src="/logo.svg" alt="SynthGen" style={{ width: '64px', height: '64px', objectFit: 'contain' }} />
        <span style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>SynthGen</span>
      </Link>

      <Card style={{ width: '100%', maxWidth: '400px' }}>
        <CardContent style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem', alignItems: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <h2 style={{ fontSize: '1.375rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.375rem' }}>
              Create your account
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
              Start generating synthetic data today
            </p>
          </div>

          {error && (
            <div style={{
              padding: '0.75rem 1rem',
              backgroundColor: 'rgba(239, 68, 68, 0.08)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              color: 'var(--error-color)',
              fontSize: '0.875rem',
              borderRadius: 'var(--radius-md)',
              lineHeight: 1.5,
              width: '100%',
            }}>
              {error}
            </div>
          )}

          {isLoading ? (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Creating account…</p>
          ) : (
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => setError('Google Sign-up Failed. Please try again.')}
              text="signup_with"
              width="300"
            />
          )}

          <p style={{ textAlign: 'center', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Already have an account?{' '}
            <Link to="/login" style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default Register;
