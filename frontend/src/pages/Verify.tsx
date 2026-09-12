import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { API_BASE } from '../lib/api';
import { CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

export default function Verify() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Verifying your email...');
  const navigate = useNavigate();

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('No verification token provided.');
      return;
    }

    const verifyToken = async () => {
      try {
        await axios.get(`${API_BASE}/v1/auth/verify/${token}`);
        setStatus('success');
        setMessage('Your email has been successfully verified! You can now access all features.');
        
        // Redirect to dashboard after 3 seconds
        setTimeout(() => {
          navigate('/dashboard');
        }, 3000);
      } catch (err: any) {
        setStatus('error');
        setMessage(err.response?.data?.detail || 'Invalid or expired verification link.');
      }
    };

    verifyToken();
  }, [token, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="glass-panel p-8 max-w-md w-full text-center">
        {status === 'loading' && (
          <div className="flex flex-col items-center">
            <Loader2 className="animate-spin text-[var(--primary-color)] mb-4" size={48} />
            <h2 className="text-xl font-bold mb-2">Verifying...</h2>
            <p className="text-gray-400">{message}</p>
          </div>
        )}

        {status === 'success' && (
          <div className="flex flex-col items-center animate-fade-in">
            <CheckCircle2 className="text-[var(--primary-color)] mb-4" size={48} />
            <h2 className="text-2xl font-bold mb-2 text-[var(--primary-color)]">Verified!</h2>
            <p className="text-gray-300 mb-6">{message}</p>
            <p className="text-sm text-gray-500">Redirecting you to dashboard...</p>
          </div>
        )}

        {status === 'error' && (
          <div className="flex flex-col items-center animate-fade-in">
            <AlertCircle className="text-red-500 mb-4" size={48} />
            <h2 className="text-2xl font-bold mb-2 text-red-500">Verification Failed</h2>
            <p className="text-gray-300 mb-6">{message}</p>
            <Link 
              to="/login"
              className="px-6 py-2 bg-white/10 hover:bg-white/20 transition-colors rounded-lg font-medium"
            >
              Return to Login
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
