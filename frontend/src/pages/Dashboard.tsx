import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Database, Zap, Clock, TrendingUp, Plus, Eye, Download } from 'lucide-react';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Spinner } from '../components/ui/Spinner';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { API_BASE } from '../lib/api';

interface Dataset {
  id: number;
  name: string;
  row_count: number;
  column_count: number;
  source_type: string;
  created_at: string;
}

interface JobSummary {
  id: number;
  status: string;
  current_step: string;
}

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [jobMap, setJobMap] = useState<Record<number, JobSummary>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [stats, setStats] = useState({
    totalDatasets: 0,
    totalRows: 0,
    completedJobs: 0,
  });

  useEffect(() => {
    const fetchDashboardData = async () => {
      setIsLoading(true);
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          setError('No authentication token found. Please log in again.');
          setIsLoading(false);
          return;
        }
        
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        
        // Fetch datasets
        const res = await axios.get(`${API_BASE}/api/datasets`);
        const data: Dataset[] = res.data || [];
        setDatasets(data.slice(0, 5)); // Show only 5 most recent

        // Fetch job status for each dataset
        const jobs: Record<number, JobSummary> = {};
        let completedCount = 0;
        await Promise.all(
          data.map(async (d) => {
            try {
              const jobRes = await axios.get(`${API_BASE}/api/jobs/by-dataset/${d.id}`);
              jobs[d.id] = jobRes.data;
              if (jobRes.data.status === 'completed') completedCount++;
            } catch { /* dataset may not have a job yet */ }
          })
        );
        setJobMap(jobs);

        // Calculate stats
        const totalRows = data.reduce((sum, d) => sum + (d.row_count || 0), 0);
        setStats({
          totalDatasets: data.length,
          totalRows,
          completedJobs: completedCount,
        });
        
        setError(''); // Clear any previous errors
      } catch (err: any) {
        console.error('Failed to load dashboard data:', err);
        const errorMsg = err.response?.data?.detail || err.message || 'Failed to load dashboard data';
        setError(errorMsg);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(0)}K`;
    return num.toString();
  };

  const getRelativeTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="flex flex-col gap-6" style={{ padding: '2rem' }}>
      <div className="flex justify-between items-center mb-4">
        <div>
          <h1 style={{ marginBottom: '0.25rem' }}>Welcome back{user?.email ? `, ${user.email.split('@')[0]}` : ''}</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Here is what's happening with your synthetic datasets today.</p>
        </div>
        <Link to="/app/generate">
          <Button variant="primary">
            <Plus size={16} className="mr-2" /> Generate Dataset
          </Button>
        </Link>
      </div>

      {error && (
        <div style={{
          padding: '0.875rem 1rem',
          backgroundColor: 'rgba(239, 68, 68, 0.08)',
          border: '1px solid rgba(239, 68, 68, 0.2)',
          color: 'var(--error-color)', fontSize: '0.875rem',
          borderRadius: 'var(--radius-md)', lineHeight: 1.5,
        }}>
          {error}
        </div>
      )}

      {/* Stats Grid */}
      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
          <Spinner size="md" />
        </div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem' }}>
            <StatCard icon={<Database size={20} color="var(--info-color)" />} label="Total Datasets" value={stats.totalDatasets.toString()} />
            <StatCard icon={<Zap size={20} color="var(--warning-color)" />} label="Rows Generated" value={formatNumber(stats.totalRows)} />
            <StatCard icon={<Clock size={20} color="var(--success-color)" />} label="Completed Jobs" value={stats.completedJobs.toString()} />
            <StatCard icon={<TrendingUp size={20} color="var(--text-secondary)" />} label="Active Jobs" value={(Object.values(jobMap).filter(j => j.status === 'running' || j.status === 'pending').length).toString()} />
          </div>

          {/* Recent Generations */}
          <div className="mt-4">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h2 style={{ fontSize: '1.25rem' }}>Recent Generations</h2>
              <Link to="/app/history">
                <Button variant="ghost" size="sm">View All</Button>
              </Link>
            </div>
            <Card>
              <div style={{ overflowX: 'auto' }}>
                {datasets.length === 0 ? (
                  <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                    <Database size={40} color="var(--border-strong)" style={{ margin: '0 auto 1rem' }} />
                    <p>No datasets yet. Generate your first dataset to get started!</p>
                  </div>
                ) : (
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <th style={{ padding: '1rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Dataset Name</th>
                        <th style={{ padding: '1rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Rows</th>
                        <th style={{ padding: '1rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Type</th>
                        <th style={{ padding: '1rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Status</th>
                        <th style={{ padding: '1rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Created</th>
                        <th style={{ padding: '1rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {datasets.map((dataset) => {
                        const job = jobMap[dataset.id];
                        const status = job?.status || 'unknown';
                        return (
                          <GenerationRow 
                            key={dataset.id}
                            id={dataset.id}
                            name={dataset.name || 'Untitled Dataset'} 
                            rows={dataset.row_count.toLocaleString()} 
                            format={dataset.source_type === 'prompt' ? 'AI Prompt' : 'CSV Upload'}
                            status={status as any}
                            date={getRelativeTime(dataset.created_at)}
                            jobId={job?.id}
                            navigate={navigate}
                          />
                        );
                      })}
                    </tbody>
                  </table>
                )}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
};

const StatCard: React.FC<{ icon: React.ReactNode; label: string; value: string }> = ({ icon, label, value }) => (
  <Card>
    <CardContent className="flex flex-col gap-2">
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-secondary)' }}>{label}</span>
      </div>
      <div style={{ fontSize: '2rem', fontWeight: 600, color: 'var(--text-primary)' }}>{value}</div>
    </CardContent>
  </Card>
);

const GenerationRow: React.FC<{ 
  id: number;
  name: string; 
  rows: string; 
  format: string; 
  status: 'completed'|'running'|'failed'|'pending'|'unknown'; 
  date: string;
  jobId?: number;
  navigate: any;
}> = ({ id, name, rows, format, status, date, jobId, navigate }) => {
  const statusColors = {
    completed: 'success',
    running: 'warning',
    failed: 'error',
    pending: 'warning',
    unknown: 'default'
  };

  const statusLabels = {
    completed: 'Completed',
    running: 'Generating',
    failed: 'Failed',
    pending: 'Queued',
    unknown: 'Ready'
  };
  
  const handleDownload = async () => {
    if (!jobId || status !== 'completed') return;
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API_BASE}/api/jobs/${jobId}/download`, {
        responseType: 'blob',
        headers: { Authorization: `Bearer ${token}` },
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${name.replace(/[^a-z0-9]/gi, '_')}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      alert('Failed to download dataset.');
    }
  };
  
  return (
    <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
      <td style={{ padding: '1rem', fontWeight: 500, color: 'var(--text-primary)', maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</td>
      <td style={{ padding: '1rem', color: 'var(--text-secondary)' }}>{rows}</td>
      <td style={{ padding: '1rem', color: 'var(--text-secondary)' }}>{format}</td>
      <td style={{ padding: '1rem' }}>
        <Badge variant={statusColors[status] as any}>{statusLabels[status]}</Badge>
      </td>
      <td style={{ padding: '1rem', color: 'var(--text-secondary)' }}>{date}</td>
      <td style={{ padding: '1rem' }}>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => navigate(`/app/datasets/${id}`)}>
            <Eye size={15} />
          </Button>
          {status === 'completed' && jobId && (
            <Button variant="ghost" size="sm" onClick={handleDownload}>
              <Download size={15} />
            </Button>
          )}
        </div>
      </td>
    </tr>
  );
};

export default Dashboard;
