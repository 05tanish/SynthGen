import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { Brain, Mail, RefreshCw, CheckCircle } from 'lucide-react';
import axios from 'axios';
import { API_BASE } from '../lib/api';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';

const RESEND_COOLDOWN = 60;
const OTP_LENGTH = 6;

const Verify: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const email = location.state?.email as string | undefined;

  const [otp, setOtp] = useState(Array(OTP_LENGTH).fill(''));
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (!email) navigate('/register');
  }, [email, navigate]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  if (!email) return null;

  const otpValue = otp.join('');

  const handleOtpChange = (index: number, value: string) => {
    const digit = value.replace(/\D/g, '').slice(-1);
    const updated = [...otp];
    updated[index] = digit;
    setOtp(updated);
    setError('');
    if (digit && index < OTP_LENGTH - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, OTP_LENGTH);
    if (pasted.length > 0) {
      const updated = Array(OTP_LENGTH).fill('');
      pasted.split('').forEach((char, i) => { updated[i] = char; });
      setOtp(updated);
      inputRefs.current[Math.min(pasted.length, OTP_LENGTH - 1)]?.focus();
    }
  };

  const handleVerify = async () => {
    if (otpValue.length !== OTP_LENGTH) {
      setError('Please enter all 6 digits of your verification code.');
      return;
    }
    setIsVerifying(true);
    setError('');
    try {
      await axios.post(`${API_BASE}/v1/auth/verify-otp`, { email, otp: otpValue });
      setSuccess('Email verified! Redirecting to login...');
      setTimeout(() => navigate('/login', { state: { verified: true } }), 1800);
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Verification failed. Please try again.';
      setError(detail);
      if (detail.toLowerCase().includes('expired')) {
        setOtp(Array(OTP_LENGTH).fill(''));
        inputRefs.current[0]?.focus();
      }
    } finally {
      setIsVerifying(false);
    }
  };

  const handleResend = async () => {
    if (cooldown > 0) return;
    setIsResending(true);
    setError('');
    try {
      await axios.post(`${API_BASE}/v1/auth/resend-otp`, { email });
      setOtp(Array(OTP_LENGTH).fill(''));
      inputRefs.current[0]?.focus();
      setCooldown(RESEND_COOLDOWN);
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Failed to resend code.';
      setError(detail);
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      minHeight: '100vh', backgroundColor: 'var(--bg-primary)', padding: '1rem',
    }}>
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '2rem', textDecoration: 'none' }}>
        <Brain size={28} color="var(--text-primary)" />
        <span style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>Synthetix</span>
      </Link>

      <Card style={{ width: '100%', maxWidth: '420px' }}>
        <CardContent style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {success ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', padding: '1rem 0' }}>
              <CheckCircle size={48} color="var(--success-color)" />
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-primary)', textAlign: 'center' }}>
                Email verified!
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', textAlign: 'center' }}>{success}</p>
            </div>
          ) : (
            <>
              <div style={{ textAlign: 'center' }}>
                <div style={{
                  width: '48px', height: '48px', borderRadius: '50%',
                  backgroundColor: 'var(--bg-secondary)', display: 'flex',
                  alignItems: 'center', justifyContent: 'center', margin: '0 auto 1rem',
                }}>
                  <Mail size={22} color="var(--text-primary)" />
                </div>
                <h2 style={{ fontSize: '1.375rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.375rem' }}>
                  Check your email
                </h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: 1.6 }}>
                  We sent a 6-digit code to<br />
                  <strong style={{ color: 'var(--text-primary)' }}>{email}</strong>
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
                }}>
                  {error}
                </div>
              )}

              {/* OTP input boxes */}
              <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }} onPaste={handlePaste}>
                {otp.map((digit, index) => (
                  <input
                    key={index}
                    ref={(el) => { inputRefs.current[index] = el; }}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleOtpChange(index, e.target.value)}
                    onKeyDown={(e) => handleOtpKeyDown(index, e)}
                    autoFocus={index === 0}
                    style={{
                      width: '48px', height: '56px',
                      textAlign: 'center', fontSize: '1.5rem', fontWeight: 600,
                      backgroundColor: 'var(--bg-secondary)',
                      border: `1px solid ${digit ? 'var(--border-focus)' : 'var(--border-subtle)'}`,
                      borderRadius: 'var(--radius-md)',
                      color: 'var(--text-primary)',
                      outline: 'none',
                      caretColor: 'var(--text-primary)',
                      transition: 'border-color 0.15s',
                    }}
                    aria-label={`OTP digit ${index + 1}`}
                  />
                ))}
              </div>

              <Button
                onClick={handleVerify}
                isLoading={isVerifying}
                disabled={otpValue.length !== OTP_LENGTH}
                style={{ width: '100%' }}
              >
                Verify Email
              </Button>

              <div style={{ textAlign: 'center' }}>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                  Didn't receive a code?
                </p>
                <button
                  onClick={handleResend}
                  disabled={cooldown > 0 || isResending}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: '0.375rem',
                    fontSize: '0.875rem', fontWeight: 500,
                    color: cooldown > 0 ? 'var(--text-muted)' : 'var(--text-primary)',
                    background: 'none', border: 'none', cursor: cooldown > 0 ? 'not-allowed' : 'pointer',
                    padding: 0,
                  }}
                >
                  <RefreshCw size={14} className={isResending ? 'spin' : ''} />
                  {cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend code'}
                </button>
              </div>

              <div style={{ textAlign: 'center', paddingTop: '0.5rem', borderTop: '1px solid var(--border-subtle)' }}>
                <Link to="/register" style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                  Use a different email
                </Link>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default Verify;
