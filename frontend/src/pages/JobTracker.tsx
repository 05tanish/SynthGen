import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Loader, Download, ArrowLeft, AlertTriangle, RefreshCw } from 'lucide-react';
import { API_BASE } from '../lib/api';

interface Job {
  id: number;
  dataset_id: number;
  status: string;
  current_step: string;
  error_message: string | null;
  evaluation_report: {
    statistical_score: number;
    privacy_score: number;
    ml_utility_score: number;
    overall_score: number;
    passed: boolean;
  } | null;
  created_at: string;
  updated_at: string | null;
}

const ScoreCard = ({ label, value, color }: { label: string; value: number; color: string }) => (
  <div className="glass-panel" style={{ padding: '1.25rem', textAlign: 'center' }}>
    <div style={{ fontSize: '2rem', fontWeight: 700, color }}>
      {(value * 100).toFixed(0)}%
    </div>
    <div style={{ fontSize: '0.85rem', color: 'var(--text-color)', marginTop: '0.25rem' }}>{label}</div>
  </div>
);

const JobTracker = () => {
  const { jobId } = useParams();
  const [job, setJob] = useState<Job | null>(null);
  const [fetchError, setFetchError] = useState('');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = async () => {
    try {
      const res = await axios.get<Job>(`${API_BASE}/jobs/${jobId}`);
      setJob(res.data);
      setFetchError('');

      if (res.data.status === 'completed' || res.data.status === 'failed') {
        if (intervalRef.current) clearInterval(intervalRef.current);
      }
    } catch (err: any) {
      console.error('Failed to fetch job status:', err);
      setFetchError(
        err.response?.data?.detail || 'Could not connect to the backend. Is the server running?'
      );
    }
  };

  useEffect(() => {
    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, 2500);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [jobId]);

  if (fetchError && !job) {
    return (
      <div className="glass-panel" style={{ maxWidth: '640px', margin: '2rem auto', textAlign: 'center' }}>
        <AlertTriangle size={48} color="var(--danger-color)" style={{ marginBottom: '1rem' }} />
        <h3 style={{ color: 'var(--danger-color)' }}>Connection Error</h3>
        <p style={{ color: 'var(--text-color)', marginBottom: '1.5rem' }}>{fetchError}</p>
        <button className="btn-secondary" onClick={fetchStatus} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
          <RefreshCw size={16} /> Retry
        </button>
      </div>
    );
  }

  if (!job) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem' }}>
        <Loader className="spin" size={32} />
        <p style={{ color: 'var(--text-color)', marginTop: '1rem' }}>Loading job status...</p>
      </div>
    );
  }

  const isComplete = job.status === 'completed';
  const isFailed = job.status === 'failed';
  const isRunning = job.status === 'running' || job.status === 'pending';

  const handleDownload = async (e: React.MouseEvent) => {
    e.preventDefault();
    try {
      const response = await axios.get(`${API_BASE}/jobs/${jobId}/download`, {
        responseType: 'blob', // Important for file downloads
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'synthetic_dataset.csv';
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/);
        if (match && match[1]) filename = match[1];
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed:', err);
      alert('Failed to download the file. Please try again.');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <Link to="/" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-color)' }}>
        <ArrowLeft size={16} /> Back to Dashboard
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel"
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
          <div>
            <h2 style={{ margin: 0 }}>Generation Status</h2>
            <p style={{ color: 'var(--text-color)', margin: '0.25rem 0 0 0', fontSize: '0.9rem' }}>Job #{job.id}</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {isRunning && <><div className="status-indicator status-running" /> <span style={{ color: 'var(--primary-color)' }}>Running</span></>}
            {isComplete && <><div className="status-indicator status-completed" /> <span style={{ color: 'var(--success-color)' }}>Completed</span></>}
            {isFailed && <><div className="status-indicator status-failed" /> <span style={{ color: 'var(--danger-color)' }}>Failed</span></>}
          </div>
        </div>

        <div style={{ padding: '1.25rem', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', marginBottom: '2rem', fontFamily: 'monospace', fontSize: '0.9rem' }}>
          &gt; Current Step: {job.current_step}
          {isRunning && <span className="blink">...</span>}
        </div>

        {isFailed && (
          <div style={{ color: 'var(--danger-color)', padding: '1rem', background: 'rgba(255, 75, 75, 0.1)', borderRadius: '8px', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
              <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong>Generation Failed</strong>
                <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.9rem' }}>{job.error_message || 'An unknown error occurred.'}</p>
              </div>
            </div>
          </div>
        )}

        {isComplete && job.evaluation_report && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ marginTop: '1rem' }}>
            <h3>Evaluation Report</h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', margin: '1.5rem 0' }}>
              <ScoreCard label="Statistical Quality" value={job.evaluation_report.statistical_score} color="var(--primary-color)" />
              <ScoreCard label="Privacy Score" value={job.evaluation_report.privacy_score} color="var(--accent-color)" />
              <ScoreCard label="ML Utility" value={job.evaluation_report.ml_utility_score} color="var(--success-color)" />
            </div>

            <div style={{ textAlign: 'center', padding: '1rem', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', marginBottom: '1.5rem' }}>
              <span style={{ color: 'var(--text-color)', fontSize: '0.9rem' }}>Overall Score: </span>
              <strong style={{ fontSize: '1.2rem', color: job.evaluation_report.overall_score >= 0.75 ? 'var(--success-color)' : 'var(--danger-color)' }}>
                {(job.evaluation_report.overall_score * 100).toFixed(1)}%
              </strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <button
                onClick={handleDownload}
                className="btn-primary"
              >
                <Download size={20} />
                Download Combined Dataset (Real + Synthetic)
              </button>
            </div>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
};

export default JobTracker;
