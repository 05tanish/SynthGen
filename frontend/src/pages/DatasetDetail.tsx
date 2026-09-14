import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_BASE } from '../lib/api';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Spinner } from '../components/ui/Spinner';
import { Download, ArrowLeft, CheckCircle2, XCircle, Loader2 } from 'lucide-react';

interface DatasetInfo {
  id: number;
  name: string;
  row_count: number;
  column_count: number;
  source_type: string;
  created_at: string;
  prompt?: string;
}

interface JobInfo {
  id: number;
  status: string;
  current_step: string;
  error_message?: string;
  evaluation_report?: {
    overall_score?: number;
    statistical_score?: number;
    privacy_score?: number;
    ml_utility_score?: number;
  };
}

const DatasetDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [dataset, setDataset] = useState<DatasetInfo | null>(null);
  const [job, setJob] = useState<JobInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    const load = async () => {
      setIsLoading(true);
      setError('');
      try {
        const token = localStorage.getItem('token');
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;

        const [dataRes, jobRes] = await Promise.allSettled([
          axios.get(`${API_BASE}/datasets/${id}`),
          axios.get(`${API_BASE}/jobs/by-dataset/${id}`),
        ]);

        if (dataRes.status === 'fulfilled') {
          setDataset(dataRes.value.data);
        } else {
          setError("Dataset not found or you don't have permission to view it.");
        }

        if (jobRes.status === 'fulfilled') {
          setJob(jobRes.value.data);
        }
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [id]);

  // Poll job if still running
  useEffect(() => {
    if (!job || job.status === 'completed' || job.status === 'failed') return;
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API_BASE}/jobs/${job.id}`);
        setJob(res.data);
        if (res.data.status === 'completed' || res.data.status === 'failed') {
          clearInterval(interval);
        }
      } catch { /* ignore */ }
    }, 3000);
    return () => clearInterval(interval);
  }, [job]);

  const handleDownload = async () => {
    if (!job || job.status !== 'completed') return;
    setIsDownloading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API_BASE}/jobs/${job.id}/download`, {
        responseType: 'blob',
        headers: { Authorization: `Bearer ${token}` },
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${(dataset?.name || 'dataset').replace(/[^a-z0-9]/gi, '_')}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      alert('Download failed. The file may not be ready yet.');
    } finally {
      setIsDownloading(false);
    }
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !dataset) {
    return (
      <div style={{ padding: '2rem', maxWidth: '640px', margin: '0 auto' }}>
        <Button variant="ghost" onClick={() => navigate('/app/history')} style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <ArrowLeft size={16} /> Back to History
        </Button>
        <div style={{
          padding: '1.5rem', backgroundColor: 'rgba(239, 68, 68, 0.08)',
          border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: 'var(--radius-md)',
          color: 'var(--error-color)', fontSize: '0.875rem',
        }}>
          {error || 'Dataset not found.'}
        </div>
      </div>
    );
  }

  const jobStatus = job?.status;
  const canDownload = jobStatus === 'completed';
  const report = job?.evaluation_report;

  return (
    <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Back */}
      <button
        onClick={() => navigate('/app/history')}
        style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', color: 'var(--text-secondary)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
      >
        <ArrowLeft size={16} /> Back to History
      </button>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
            {dataset.name || 'Untitled Dataset'}
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Created {new Date(dataset.created_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
          </p>
        </div>
        <Button
          onClick={handleDownload}
          disabled={!canDownload || isDownloading}
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: canDownload ? 1 : 0.5 }}
          title={canDownload ? 'Download CSV' : 'Dataset not ready for download'}
        >
          {isDownloading ? <Spinner size="sm" /> : <Download size={16} />}
          {isDownloading ? 'Downloading...' : 'Download CSV'}
        </Button>
      </div>

      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem' }}>
        {[
          { label: 'Rows', value: (dataset.row_count || 0).toLocaleString() },
          { label: 'Columns', value: dataset.column_count ?? '—' },
          { label: 'Source', value: dataset.source_type === 'prompt' ? 'AI Prompt' : 'CSV Upload' },
          { label: 'Status', value: jobStatus ? (jobStatus.charAt(0).toUpperCase() + jobStatus.slice(1)) : 'Unknown' },
        ].map((item) => (
          <Card key={item.label}>
            <CardContent style={{ padding: '1.25rem' }}>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.375rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{item.label}</p>
              <p style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-primary)' }}>{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Job status */}
      {job && (
        <Card>
          <CardContent style={{ padding: '1.5rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '1rem' }}>Generation Status</h3>
            {jobStatus === 'running' || jobStatus === 'pending' ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--warning-color)', fontSize: '0.875rem' }}>
                <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
                {jobStatus === 'pending' ? 'Queued for processing...' : `Generating: ${job.current_step.replace(/_/g, ' ')}...`}
              </div>
            ) : jobStatus === 'completed' ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--success-color)', fontSize: '0.875rem' }}>
                <CheckCircle2 size={18} />
                Generation completed successfully. Download is ready.
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--error-color)', fontSize: '0.875rem' }}>
                <XCircle size={18} />
                Generation failed: {job.error_message || 'Unknown error'}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Evaluation report */}
      {report && (
        <Card>
          <CardContent style={{ padding: '1.5rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '1rem' }}>Quality Report</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem' }}>
              {[
                { label: 'Overall Score', value: report.overall_score },
                { label: 'Statistical', value: report.statistical_score },
                { label: 'Privacy', value: report.privacy_score },
                { label: 'ML Utility', value: report.ml_utility_score },
              ].map(({ label, value }) => (
                <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</p>
                  {value != null ? (
                    <>
                      <p style={{ fontSize: '1.25rem', fontWeight: 600, color: value >= 0.7 ? 'var(--success-color)' : value >= 0.5 ? 'var(--warning-color)' : 'var(--error-color)' }}>
                        {(value * 100).toFixed(0)}%
                      </p>
                      <div style={{ height: '4px', backgroundColor: 'var(--bg-tertiary)', borderRadius: '2px' }}>
                        <div style={{ height: '100%', width: `${Math.round(value * 100)}%`, borderRadius: '2px', backgroundColor: value >= 0.7 ? 'var(--success-color)' : value >= 0.5 ? 'var(--warning-color)' : 'var(--error-color)' }} />
                      </div>
                    </>
                  ) : (
                    <p style={{ color: 'var(--text-muted)' }}>—</p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Prompt */}
      {dataset.prompt && (
        <Card>
          <CardContent style={{ padding: '1.5rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>Generation Prompt</h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>{dataset.prompt}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default DatasetDetail;
