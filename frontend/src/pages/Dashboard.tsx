import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Database, PlusCircle, History as HistoryIcon, ShieldAlert } from 'lucide-react';
import axios from 'axios';
import { API_BASE } from '../lib/api';
import { useAuth } from '../context/AuthContext';

export default function Dashboard() {
  const [datasetCount, setDatasetCount] = useState(0);
  const [recentDatasets, setRecentDatasets] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const response = await axios.get(`${API_BASE}/v1/datasets/`);
        setDatasetCount(response.data.length);
        setRecentDatasets(response.data.slice(0, 3));
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-8 animate-fade-in">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold mb-2">Welcome back, {user?.email.split('@')[0]}!</h1>
          <p className="text-gray-400">Here's what's happening with your synthetic data.</p>
        </div>
        
        {!user?.is_verified && (
          <div className="flex items-center gap-2 px-4 py-2 bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 rounded-lg text-sm font-medium cursor-pointer" onClick={() => navigate('/profile')}>
            <ShieldAlert size={16} />
            Please verify your email
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="glass-panel p-6 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-300">Total Datasets</h3>
            <div className="p-2 bg-[var(--primary-color)]/10 text-[var(--primary-color)] rounded-lg">
              <Database size={20} />
            </div>
          </div>
          {isLoading ? (
            <div className="h-10 w-16 bg-white/5 rounded animate-pulse"></div>
          ) : (
            <div className="text-4xl font-bold">{datasetCount}</div>
          )}
        </div>

        <div className="glass-panel p-6 flex flex-col justify-center items-center text-center col-span-1 md:col-span-2 relative overflow-hidden group cursor-pointer" onClick={() => navigate('/generate')}>
          <div className="absolute inset-0 bg-gradient-to-r from-[var(--primary-color)]/20 to-[var(--accent-color)]/20 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
          <PlusCircle size={48} className="text-[var(--primary-color)] mb-4 group-hover:scale-110 transition-transform duration-300" />
          <h3 className="text-xl font-bold mb-2">Start New Generation</h3>
          <p className="text-gray-400 max-w-sm">Upload a seed file or write a prompt to automatically synthesize a new dataset.</p>
        </div>
      </div>

      <div className="glass-panel p-6">
        <div className="flex justify-between items-center mb-6 border-b border-white/10 pb-4">
          <h3 className="text-xl font-bold flex items-center gap-2">
            <HistoryIcon size={20} className="text-[var(--primary-color)]" />
            Recent Activity
          </h3>
          <Link to="/history" className="text-sm text-[var(--primary-color)] hover:underline">
            View All
          </Link>
        </div>

        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-16 w-full bg-white/5 rounded-lg animate-pulse"></div>
            ))}
          </div>
        ) : recentDatasets.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            No datasets generated yet. Click "Start New Generation" above!
          </div>
        ) : (
          <div className="space-y-4">
            {recentDatasets.map(dataset => (
              <div key={dataset.id} className="flex items-center justify-between p-4 bg-white/5 rounded-lg hover:bg-white/10 transition-colors border border-white/5">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded bg-blue-500/10 flex items-center justify-center text-blue-400">
                    <Database size={20} />
                  </div>
                  <div>
                    <h4 className="font-semibold text-white">{dataset.name}</h4>
                    <p className="text-sm text-gray-400">{dataset.row_count.toLocaleString()} rows • {new Date(dataset.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
                <Link to={`/dashboard`} className="px-4 py-2 bg-white/10 rounded-lg text-sm font-medium hover:bg-white/20 transition-colors">
                  View
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
