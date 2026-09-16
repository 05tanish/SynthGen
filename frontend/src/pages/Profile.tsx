import React, { useState } from 'react';
import { User, Lock, Key, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import axios from 'axios';
import { API_BASE } from '../lib/api';

// ─── Tab Button ───────────────────────────────────────────────────────────────
const TabButton: React.FC<{ active: boolean; onClick: () => void; icon: React.ReactNode; label: string }> = ({ active, onClick, icon, label }) => (
  <button
    onClick={onClick}
    style={{
      display: 'flex', alignItems: 'center', gap: '0.625rem',
      padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-md)', width: '100%',
      textAlign: 'left', fontSize: '0.875rem', fontWeight: active ? 500 : 400,
      backgroundColor: active ? 'var(--surface-active)' : 'transparent',
      color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
      border: 'none', cursor: 'pointer', transition: 'background-color 0.15s, color 0.15s',
    }}
    onMouseEnter={e => { if (!active) e.currentTarget.style.backgroundColor = 'var(--surface-hover)'; }}
    onMouseLeave={e => { if (!active) e.currentTarget.style.backgroundColor = 'transparent'; }}
  >
    {icon} {label}
  </button>
);

// ─── Feedback message ─────────────────────────────────────────────────────────
const Feedback: React.FC<{ msg: string }> = ({ msg }) => {
  if (!msg) return null;
  const isSuccess = msg.toLowerCase().includes('success') || msg.toLowerCase().includes('updated') || msg.toLowerCase().includes('changed');
  return (
    <div style={{
      padding: '0.75rem 1rem', fontSize: '0.875rem', borderRadius: 'var(--radius-md)',
      backgroundColor: isSuccess ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
      border: `1px solid ${isSuccess ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'}`,
      color: isSuccess ? 'var(--success-color)' : 'var(--error-color)',
    }}>
      {msg}
    </div>
  );
};

// ─── Profile Page ─────────────────────────────────────────────────────────────
const Profile: React.FC = () => {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<'profile' | 'security' | 'api'>('profile');

  // Profile form
  const [name, setName] = useState(user?.name || '');
  const [isUpdating, setIsUpdating] = useState(false);
  const [profileMsg, setProfileMsg] = useState('');

  // Password form
  const [currentPwd, setCurrentPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [isChangingPwd, setIsChangingPwd] = useState(false);
  const [pwdMsg, setPwdMsg] = useState('');

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdating(true);
    setProfileMsg('');
    try {
      await axios.patch(`${API_BASE}/api/v1/auth/me`, { name: name.trim() || null });
      setProfileMsg('Profile updated successfully.');
    } catch {
      setProfileMsg('Failed to update profile. Please try again.');
    } finally {
      setIsUpdating(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwdMsg('');
    if (newPwd.length < 8) { setPwdMsg('New password must be at least 8 characters.'); return; }
    if (newPwd !== confirmPwd) { setPwdMsg('New passwords do not match.'); return; }
    setIsChangingPwd(true);
    try {
      await axios.post(`${API_BASE}/api/v1/auth/change-password`, { current_password: currentPwd, new_password: newPwd });
      setPwdMsg('Password changed successfully.');
      setCurrentPwd(''); setNewPwd(''); setConfirmPwd('');
    } catch (err: any) {
      setPwdMsg(err.response?.data?.detail || 'Failed to change password.');
    } finally {
      setIsChangingPwd(false);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.375rem' }}>Settings</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9375rem' }}>Manage your account settings and preferences.</p>
      </div>

      <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* Sidebar nav */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', minWidth: '180px', flexShrink: 0 }}>
          <TabButton active={activeTab === 'profile'} onClick={() => setActiveTab('profile')} icon={<User size={16} />} label="Account" />
          <TabButton active={activeTab === 'security'} onClick={() => setActiveTab('security')} icon={<Lock size={16} />} label="Security" />
          <TabButton active={activeTab === 'api'} onClick={() => setActiveTab('api')} icon={<Key size={16} />} label="API Access" />
          <div style={{ height: '1px', backgroundColor: 'var(--border-subtle)', margin: '0.5rem 0' }} />
          <button
            onClick={logout}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.625rem', padding: '0.5rem 0.75rem',
              borderRadius: 'var(--radius-md)', width: '100%', textAlign: 'left',
              fontSize: '0.875rem', fontWeight: 400, backgroundColor: 'transparent',
              color: 'var(--error-color)', border: 'none', cursor: 'pointer', transition: 'background-color 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.08)'}
            onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <LogOut size={16} /> Sign Out
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, minWidth: '0', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* ── Account ── */}
          {activeTab === 'profile' && (
            <>
              <Card>
                <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
                  <h2 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>Account</h2>
                  <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0' }}>Update your personal information.</p>
                </div>
                <CardContent style={{ padding: '1.5rem' }}>
                  <form onSubmit={handleUpdateProfile} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '420px' }}>
                    <Feedback msg={profileMsg} />
                    {/* Avatar */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
                      <div style={{
                        width: '56px', height: '56px', borderRadius: '50%',
                        backgroundColor: 'var(--border-strong)', display: 'flex',
                        alignItems: 'center', justifyContent: 'center',
                        fontSize: '1.375rem', fontWeight: 600, color: 'var(--text-primary)',
                        flexShrink: 0,
                      }}>
                        {(user?.name || user?.email || '?').charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p style={{ fontSize: '0.9375rem', fontWeight: 500, color: 'var(--text-primary)' }}>
                          {user?.name || 'No name set'}
                        </p>
                        <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>{user?.email}</p>
                      </div>
                    </div>
                    <Input label="Full name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
                    <Input label="Email address" value={user?.email || ''} disabled />
                    <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                      <Button type="submit" isLoading={isUpdating}>Save Changes</Button>
                    </div>
                  </form>
                </CardContent>
              </Card>

              <Card>
                <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
                  <h2 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--error-color)', margin: 0 }}>Danger Zone</h2>
                </div>
                <CardContent style={{ padding: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                  <div>
                    <h4 style={{ fontSize: '0.9375rem', fontWeight: 500, color: 'var(--text-primary)', margin: '0 0 0.25rem' }}>Delete Account</h4>
                    <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Permanently delete your account and all generated datasets.</p>
                  </div>
                  <Button variant="danger" onClick={() => alert('Account deletion coming soon. Please contact support.')}>
                    Delete Account
                  </Button>
                </CardContent>
              </Card>
            </>
          )}

          {/* ── Security ── */}
          {activeTab === 'security' && (
            <Card>
              <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
                <h2 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>Change Password</h2>
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0' }}>
                  Use a strong, unique password.
                </p>
              </div>
              <CardContent style={{ padding: '1.5rem' }}>
                <form onSubmit={handleChangePassword} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '420px' }}>
                  <Feedback msg={pwdMsg} />
                  <Input label="Current password" type="password" value={currentPwd} onChange={(e) => setCurrentPwd(e.target.value)} required />
                  <Input label="New password" type="password" value={newPwd} onChange={(e) => setNewPwd(e.target.value)} placeholder="Min. 8 characters" required />
                  <Input label="Confirm new password" type="password" value={confirmPwd} onChange={(e) => setConfirmPwd(e.target.value)} required />
                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <Button type="submit" isLoading={isChangingPwd}>Update Password</Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          {/* ── API Access ── */}
          {activeTab === 'api' && (
            <Card>
              <CardContent style={{ padding: '3rem 2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '1rem' }}>
                <div style={{
                  width: '56px', height: '56px', borderRadius: 'var(--radius-lg)',
                  backgroundColor: 'var(--bg-secondary)', display: 'flex',
                  alignItems: 'center', justifyContent: 'center', marginBottom: '0.5rem',
                }}>
                  <Key size={24} color="var(--text-primary)" />
                </div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                  API Access
                </h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9375rem', maxWidth: '380px', lineHeight: 1.6 }}>
                  Programmatically generate synthetic datasets using the SynthGen REST API.
                </p>
                <div style={{
                  padding: '0.5rem 1.25rem', borderRadius: '999px',
                  border: '1px solid var(--border-strong)',
                  fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-muted)',
                  letterSpacing: '0.04em', textTransform: 'uppercase',
                }}>
                  Coming Soon
                </div>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', maxWidth: '360px' }}>
                  API key management and programmatic access will be available in a future release.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default Profile;
