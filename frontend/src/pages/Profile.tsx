import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, Key, AlertCircle, CheckCircle2, User } from 'lucide-react';
import axios from 'axios';
import { API_BASE } from '../lib/api';

export default function Profile() {
  const { user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setMessage({ type: 'error', text: "New passwords do not match" });
      return;
    }
    
    setIsLoading(true);
    setMessage(null);
    
    try {
      await axios.post(`${API_BASE}/v1/auth/change-password`, {
        current_password: currentPassword,
        new_password: newPassword
      });
      setMessage({ type: 'success', text: "Password changed successfully" });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setMessage({ type: 'error', text: err.response?.data?.detail || "Failed to change password" });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-8 animate-fade-in">
      <h1 className="text-3xl font-bold mb-8">Profile & Settings</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        
        {/* Account Info */}
        <div className="md:col-span-1 space-y-6">
          <div className="glass-panel p-6">
            <div className="w-16 h-16 rounded-full bg-white/10 flex items-center justify-center mb-4 text-white">
              <User size={32} />
            </div>
            <h2 className="text-xl font-bold mb-1 truncate" title={user?.email}>{user?.email}</h2>
            
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Account Status</h3>
              {user?.is_verified ? (
                <div className="flex items-center gap-2 text-[var(--primary-color)]">
                  <CheckCircle2 size={18} />
                  <span>Verified</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-yellow-500">
                  <AlertCircle size={18} />
                  <span>Unverified</span>
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Security Settings */}
        <div className="md:col-span-2">
          <div className="glass-panel p-6">
            <div className="flex items-center gap-3 mb-6 pb-4 border-b border-white/10">
              <Shield className="text-[var(--primary-color)]" size={24} />
              <h2 className="text-xl font-bold">Security Settings</h2>
            </div>
            
            <form onSubmit={handleChangePassword} className="space-y-4">
              <h3 className="text-lg font-semibold mb-2">Change Password</h3>
              
              {message && (
                <div className={`p-4 rounded-lg flex items-center gap-3 ${
                  message.type === 'success' ? 'bg-[var(--primary-color)]/10 text-[var(--primary-color)] border border-[var(--primary-color)]/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'
                }`}>
                  {message.type === 'success' ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
                  {message.text}
                </div>
              )}
              
              <div>
                <label className="block text-sm text-gray-400 mb-1">Current Password</label>
                <div className="relative">
                  <Key className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                  <input
                    type="password"
                    required
                    value={currentPassword}
                    onChange={e => setCurrentPassword(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg focus:border-[var(--primary-color)] focus:outline-none transition-colors"
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">New Password</label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                    className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg focus:border-[var(--primary-color)] focus:outline-none transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Confirm New Password</label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg focus:border-[var(--primary-color)] focus:outline-none transition-colors"
                  />
                </div>
              </div>
              
              <div className="pt-4">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-6 py-2 bg-[var(--primary-color)] text-black rounded-lg font-bold hover:bg-[var(--accent-color)] transition-colors disabled:opacity-50"
                >
                  {isLoading ? 'Updating...' : 'Update Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
        
      </div>
    </div>
  );
}
