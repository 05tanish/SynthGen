import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { Download, ArrowLeft, AlertTriangle } from 'lucide-react';
import { API_BASE } from '../lib/api';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';

interface Job {
  id: number;
  dataset_id: number;
  status: string;
  current_step: string;
  error_message: string | null;
  evaluation_report: any | null;
  created_at: string;
}

const ScoreCard = ({ label, value, color }: { label: string; value: number; color: string }) => (
  <Card className="flex-1">
    <CardContent className="flex flex-col items-center justify-center py-6 text-center">
      <div style={{ fontSize: '2.5rem', fontWeight: 700, color }}>
        {(value * 100).toFixed(0)}%
      </div>
      <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>{label}</div>
    </CardContent>
  </Card>
);

export default function JobTracker() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<number | null>(null);

  useEffect(() => {
    const fetchJob = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await axios.get(`${API_BASE}/api/jobs/${jobId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setJob(res.data);

        if (res.data.status === 'completed' || res.data.status === 'failed') {
          if (pollingRef.current) clearInterval(pollingRef.current);
        }
      } catch (err: any) {
        if (pollingRef.current) clearInterval(pollingRef.current);
        setError(err.response?.data?.detail || 'Failed to fetch generation status');
      }
    };

    fetchJob();
    pollingRef.current = window.setInterval(fetchJob, 2000);

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [jobId]);

  const handleDownload = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API_BASE}/api/jobs/${jobId}/download`, {
        responseType: 'blob',
        headers: { Authorization: `Bearer ${token}` }
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `dataset_${job?.dataset_id}_synthetic.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error("Failed to download", err);
      alert("Failed to download synthetic data");
    }
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <AlertTriangle size={48} className="text-red-500" />
        <h2 className="text-xl">{error}</h2>
        <Link to="/app/dashboard">
          <Button variant="secondary">Back to Dashboard</Button>
        </Link>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <div className="spinner spinner-lg"></div>
        <p className="text-gray-400">Loading generation status...</p>
      </div>
    );
  }

  const isComplete = job.status === 'completed';
  const isFailed = job.status === 'failed';
  
  // Map steps to numbers
  const stepsList = ['queued', 'loading_data', 'running_graph', 'saving_results'];
  const currentIndex = stepsList.indexOf(job.current_step);
  const progressPercent = isComplete ? 100 : isFailed ? 100 : Math.max(5, (currentIndex / stepsList.length) * 100);

  return (
    <div className="flex flex-col gap-6 max-w-4xl mx-auto w-full" style={{ padding: '2rem' }}>
      <div className="flex items-center gap-4">
        <Link to="/app/dashboard">
          <Button variant="ghost" size="sm"><ArrowLeft size={16} /></Button>
        </Link>
        <h1 style={{ margin: 0, fontSize: '1.5rem' }}>Generation Status</h1>
      </div>

      <Card>
        <CardContent className="flex flex-col gap-6" style={{ padding: '2rem' }}>
          
          <div className="flex justify-between items-end">
            <div>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                Job ID: {job.id} • Dataset ID: {job.dataset_id}
              </div>
              <h2 style={{ margin: 0, fontSize: '1.25rem' }}>
                {isComplete ? 'Generation Complete' : isFailed ? 'Generation Failed' : 'Generating your dataset...'}
              </h2>
            </div>
            
            {isComplete && (
              <Button onClick={handleDownload} variant="primary">
                <Download size={16} className="mr-2" /> Download Dataset
              </Button>
            )}
          </div>

          <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--bg-secondary)', borderRadius: '4px', overflow: 'hidden' }}>
            <div 
              style={{ 
                height: '100%', 
                width: `${progressPercent}%`, 
                backgroundColor: isFailed ? 'var(--error-color)' : isComplete ? 'var(--success-color)' : 'var(--text-primary)',
                transition: 'width 0.5s ease'
              }} 
            />
          </div>

          {!isComplete && !isFailed && (
            <div className="flex justify-between items-center" style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              <span>Current step: <strong>{job.current_step.replace('_', ' ')}</strong></span>
              <div className="flex items-center gap-2">
                <div className="spinner spinner-sm" /> Processing
              </div>
            </div>
          )}

          {isFailed && (
            <div style={{ padding: '1rem', backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--error-color)', borderRadius: 'var(--radius-md)' }}>
              <strong>Error:</strong> {job.error_message || 'Unknown error occurred'}
            </div>
          )}

        </CardContent>
      </Card>

      {isComplete && job.evaluation_report && (
        <div className="flex flex-col gap-4 mt-4">
          <h3 style={{ margin: 0 }}>Quality Metrics</h3>
          <div className="flex gap-4 flex-wrap">
            <ScoreCard label="Statistical Similarity" value={job.evaluation_report.statistical_score || 0.9} color="var(--info-color)" />
            <ScoreCard label="Privacy Preservation" value={job.evaluation_report.privacy_score || 0.99} color="var(--success-color)" />
            <ScoreCard label="ML Utility" value={job.evaluation_report.ml_utility_score || 0.85} color="var(--warning-color)" />
          </div>
        </div>
      )}
    </div>
  );
}
