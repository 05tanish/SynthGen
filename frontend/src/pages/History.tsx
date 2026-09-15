import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_BASE } from '../lib/api';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Spinner } from '../components/ui/Spinner';
import { Download, Eye, RefreshCw, CheckCircle2, Clock, XCircle, Database } from 'lucide-react';

interface Dataset {
  id: number;
  name: string;
  row_count: number;
  column_count: number;
  source_type: string;
  created_at: string;
  prompt?: string;
}

interface JobSummary {
  id: number;
  status: string;
  current_step: string;
}

const STATUS_ICONS: Record<string, React.ReactNode> = {
  completed: <CheckCircle2 size={14} color="var(--success-color)" />,
  failed: <XCircle size={14} color="var(--error-color)" />,
  running: <Spinner size="sm" />,
  pending: <Clock size={14} color="var(--warning-color)" />,
};

const STATUS_LABELS: Record<string, string> = {
  completed: 'Completed',
  failed: 'Failed',
  running: 'Generating...',
  pending: 'Queued',
};

const History: React.FC = () => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [jobMap, setJobMap] = useState<Record<number, JobSummary>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const navigate = useNavigate();

  const fetchHistory = async () => {
    setIsLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('token');
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      const res = await axios.get(`${API_BASE}/api/datasets`);
      const data: Dataset[] = res.data;
      setDatasets(data);

      // Fetch job status for each dataset in parallel
      const jobs: Record<number, JobSummary> = {};
      await Promise.all(
        data.map(async (d) => {
          try {
            const jobRes = await axios.get(`${API_BASE}/api/jobs/by-dataset/${d.id}`);
            jobs[d.id] = jobRes.data;
          } catch { /* dataset may not have a job yet */ }
        })
      );
      setJobMap(jobs);
    } catch (err) {
      setError('Failed to load generation history. Please refresh.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchHistory(); }, []);

  const handleDownload = async (datasetId: number) => {
    const job = jobMap[datasetId];
    if (!job || job.status !== 'completed') return;
    setDownloadingId(datasetId);
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API_BASE}/api/jobs/${job.id}/download`, {
        responseType: 'blob',
        headers: { Authorization: `Bearer ${token}` },
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      const dataset = datasets.find(d => d.id === datasetId);
      link.setAttribute('download', `${(dataset?.name || 'dataset').replace(/[^a-z0-9]/gi, '_')}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      alert('Failed to download dataset. The file may not be ready yet.');
    } finally {
      setDownloadingId(null);
    }
  };

  const sourceTypeLabel = (type: string) => {
    if (type === 'prompt') return 'AI Prompt';
    if (type === 'upload') return 'CSV Upload';
    return type;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', padding: '2rem', maxWidth: '1000px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.375rem' }}>
            Datasets
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9375rem' }}>
            Your generated synthetic datasets and generation history.
          </p>
        </div>
        <Button variant="secondary" onClick={fetchHistory} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <RefreshCw size={15} /> Refresh
        </Button>
      </div>

      {error && (
        <div style={{
          padding: '0.875rem 1rem', backgroundColor: 'rgba(239, 68, 68, 0.08)',
          border: '1px solid rgba(239, 68, 68, 0.2)', color: 'var(--error-color)',
          fontSize: '0.875rem', borderRadius: 'var(--radius-md)',
        }}>
          {error}
        </div>
      )}

      <Card>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', backgroundColor: 'var(--bg-secondary)' }}>
                {['Name', 'Type', 'Rows', 'Columns', 'Status', 'Date', 'Actions'].map((h) => (
                  <th key={h} style={{ padding: '0.875rem 1rem', color: 'var(--text-muted)', fontWeight: 500, textAlign: 'left', whiteSpace: 'nowrap' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} style={{ padding: '3rem', textAlign: 'center' }}>
                    <Spinner size="md" />
                  </td>
                </tr>
              ) : datasets.length === 0 ? (
                <tr>
                  <td colSpan={7}>
                    <div style={{ padding: '4rem 2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', textAlign: 'center' }}>
                      <Database size={40} color="var(--border-strong)" />
                      <h3 style={{ color: 'var(--text-primary)', fontSize: '1.125rem' }}>No datasets yet</h3>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Generate your first synthetic dataset to see it here.</p>
                      <Button onClick={() => navigate('/app/generate')} style={{ marginTop: '0.5rem' }}>Generate a Dataset</Button>
                    </div>
                  </td>
                </tr>
              ) : (
                datasets.map((d) => {
                  const job = jobMap[d.id];
                  const canDownload = job?.status === 'completed';
                  const isDownloading = downloadingId === d.id;
                  return (
                    <tr key={d.id} style={{ borderBottom: '1px solid var(--border-subtle)', transition: 'background-color 0.1s' }}
                      onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--surface-hover)')}
                      onMouseLeave={e => (e.currentTarget.style.backgroundColor = '')}
                    >
                      <td style={{ padding: '0.875rem 1rem', fontWeight: 500, color: 'var(--text-primary)', maxWidth: '220px' }}>
                        <span title={d.name} style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {d.name || 'Untitled Dataset'}
                        </span>
                      </td>
                      <td style={{ padding: '0.875rem 1rem', color: 'var(--text-secondary)' }}>
                        {sourceTypeLabel(d.source_type)}
                      </td>
                      <td style={{ padding: '0.875rem 1rem', color: 'var(--text-secondary)' }}>
                        {(d.row_count || 0).toLocaleString()}
                      </td>
                      <td style={{ padding: '0.875rem 1rem', color: 'var(--text-secondary)' }}>
                        {d.column_count || '—'}
                      </td>
                      <td style={{ padding: '0.875rem 1rem' }}>
                        {job ? (
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.8125rem', color: job.status === 'completed' ? 'var(--success-color)' : job.status === 'failed' ? 'var(--error-color)' : 'var(--warning-color)' }}>
                            {STATUS_ICONS[job.status] || <Clock size={14} />}
                            {STATUS_LABELS[job.status] || job.status}
                          </span>
                        ) : (
                          <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: '0.875rem 1rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                        {new Date(d.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </td>
                      <td style={{ padding: '0.875rem 1rem' }}>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => navigate(`/app/datasets/${d.id}`)}
                            title="View dataset"
                            style={{ padding: '0.375rem' }}
                          >
                            <Eye size={15} />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDownload(d.id)}
                            disabled={!canDownload || isDownloading}
                            title={canDownload ? 'Download CSV' : 'Not ready for download'}
                            style={{ padding: '0.375rem', opacity: canDownload ? 1 : 0.4 }}
                          >
                            {isDownloading ? <Spinner size="sm" /> : <Download size={15} />}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

export default History;
