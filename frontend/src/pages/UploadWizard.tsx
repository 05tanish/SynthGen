import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { UploadCloud, FileText, Sparkles, X, CheckCircle2, Loader2 } from 'lucide-react';
import axios from 'axios';
import { API_BASE } from '../lib/api';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';
import { Input } from '../components/ui/Input';

type Mode = 'dataset' | 'prompt';

const GENERATION_STEPS = [
  { key: 'queued', label: 'Request queued' },
  { key: 'loading_data', label: 'Loading data' },
  { key: 'running_graph', label: 'Generating synthetic records' },
  { key: 'finished', label: 'Finalizing dataset' },
];

const Generate: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const navState = location.state as { prompt?: string; name?: string } | null;

  const [mode, setMode] = useState<Mode>(navState?.prompt ? 'prompt' : 'prompt');
  const [file, setFile] = useState<File | null>(null);
  const [prompt, setPrompt] = useState(navState?.prompt || '');
  const [rows, setRows] = useState(500);
  const [format, setFormat] = useState('CSV');
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState('');
  const [jobId, setJobId] = useState<number | null>(null);
  const [jobStep, setJobStep] = useState<string>('');
  const [jobDone, setJobDone] = useState(false);

  // Poll job status
  useEffect(() => {
    if (!jobId || jobDone) return;
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API_BASE}/jobs/${jobId}`);
        const { status, current_step } = res.data;
        setJobStep(current_step);
        if (status === 'completed' || status === 'failed') {
          setJobDone(true);
          clearInterval(interval);
          if (status === 'failed') {
            setError(res.data.error_message || 'Generation failed. Please try again.');
            setIsGenerating(false);
          }
        }
      } catch { /* ignore polling errors */ }
    }, 2000);
    return () => clearInterval(interval);
  }, [jobId, jobDone]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) { setFile(e.target.files[0]); setError(''); }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files?.[0]) { setFile(e.dataTransfer.files[0]); setError(''); }
  };

  const handleGenerate = async () => {
    if (mode === 'dataset' && !file) { setError('Please upload a CSV file.'); return; }
    if (mode === 'prompt' && !prompt.trim()) { setError('Please describe the dataset you want to generate.'); return; }

    setIsGenerating(true);
    setError('');
    setJobDone(false);
    setJobStep('');

    try {
      const token = localStorage.getItem('token');
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;

      let newJobId: number;

      if (mode === 'dataset') {
        const formData = new FormData();
        formData.append('file', file as File);
        
        // Build the prompt: include user's custom instructions and row count directive
        let generationPrompt = prompt.trim();
        if (!generationPrompt.toLowerCase().includes('generate') || !generationPrompt.match(/\d+\s*rows?/i)) {
          // User didn't specify row count in their prompt, so add it
          generationPrompt = `Generate exactly ${rows} rows based on this dataset. ${generationPrompt}`.trim();
        }
        
        formData.append('prompt', generationPrompt);
        const uploadRes = await axios.post(`${API_BASE}/datasets/upload`, formData);
        const datasetId = uploadRes.data.id;
        const genRes = await axios.post(`${API_BASE}/datasets/${datasetId}/generate`);
        newJobId = genRes.data.job_id;
      } else {
        const genRes = await axios.post(`${API_BASE}/datasets/generate-from-prompt`, {
          prompt: prompt.trim(),
          row_count: rows,
          format,
        });
        newJobId = genRes.data.job_id;
      }

      setJobId(newJobId);
      setJobStep('queued');
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(detail || 'Failed to start generation. Please try again.');
      setIsGenerating(false);
    }
  };

  const activeStepIndex = GENERATION_STEPS.findIndex(s => s.key === jobStep);

  // ─── Generating state overlay ────────────────────────────────────────────────
  if (isGenerating && !jobDone) {
    return (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center', 
        justifyContent: 'center', 
        minHeight: '60vh', 
        gap: '2rem', 
        padding: '2rem',
        backgroundColor: 'var(--bg-primary)'
      }}>
        <div style={{ position: 'relative', width: '64px', height: '64px' }}>
          <Loader2 size={64} color="var(--text-primary)" style={{ animation: 'spin 1.2s linear infinite' }} />
        </div>
        <div style={{ textAlign: 'center' }}>
          <h2 style={{ fontSize: '1.375rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
            Generating dataset...
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            This may take a minute. Please don't close this page.
          </p>
        </div>

        {/* Step progress */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%', maxWidth: '340px' }}>
          {GENERATION_STEPS.map((s, i) => {
            const isDone = activeStepIndex > i;
            const isActive = activeStepIndex === i;
            return (
              <div key={s.key} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{
                  width: '20px', height: '20px', borderRadius: '50%', flexShrink: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  backgroundColor: isDone ? 'var(--success-color)' : isActive ? 'var(--text-primary)' : 'var(--bg-tertiary)',
                  border: `1px solid ${isDone ? 'var(--success-color)' : isActive ? 'var(--text-primary)' : 'var(--border-subtle)'}`,
                }}>
                  {isDone && <CheckCircle2 size={12} color="white" />}
                  {isActive && <Loader2 size={12} color="var(--bg-primary)" style={{ animation: 'spin 1s linear infinite' }} />}
                </div>
                <span style={{
                  fontSize: '0.875rem',
                  color: isDone ? 'var(--text-primary)' : isActive ? 'var(--text-primary)' : 'var(--text-muted)',
                  fontWeight: isActive ? 500 : 400,
                }}>
                  {s.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (jobDone && isGenerating) {
    return (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center', 
        justifyContent: 'center', 
        minHeight: '60vh', 
        gap: '2rem', 
        padding: '2rem',
        backgroundColor: 'var(--bg-primary)'
      }}>
        <CheckCircle2 size={56} color="var(--success-color)" />
        <div style={{ textAlign: 'center' }}>
          <h2 style={{ fontSize: '1.375rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
            Dataset ready!
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
            Your synthetic dataset has been generated successfully.
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
            <Button onClick={() => navigate(`/app/jobs/${jobId}`)}>View Results</Button>
            <Button variant="secondary" onClick={() => {
              setIsGenerating(false); setJobId(null);
              setFile(null); setPrompt(''); setJobStep(''); setJobDone(false);
            }}>Generate Another</Button>
          </div>
        </div>
      </div>
    );
  }


  // ─── Template prompts ─────────────────────────────────────────────────────────
  const templates = [
    { label: 'Customer data', prompt: 'Generate a customer dataset with first name, last name, email, phone, country, registration date, and lifetime value.' },
    { label: 'E-commerce orders', prompt: 'Generate e-commerce transaction records with order ID, product name, category, price, quantity, date, and customer email.' },
    { label: 'Employee records', prompt: 'Generate employee records with name, department, job title, hire date, salary, and performance rating.' },
    { label: 'Healthcare patients', prompt: 'Generate patient records with patient ID, age, gender, diagnosis, medication, visit date, and doctor name.' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '720px', margin: '0 auto', padding: '2rem' }}>
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 600, marginBottom: '0.375rem', color: 'var(--text-primary)' }}>
          Generate Dataset
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9375rem' }}>
          Describe what you need, or upload a reference CSV to generate synthetic variations.
        </p>
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

      {/* Mode selector */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
        <ModeCard
          active={mode === 'prompt'}
          onClick={() => setMode('prompt')}
          icon={<Sparkles size={20} />}
          title="Generate from prompt"
          desc="Describe your dataset in plain text"
        />
        <ModeCard
          active={mode === 'dataset'}
          onClick={() => setMode('dataset')}
          icon={<UploadCloud size={20} />}
          title="Generate from file"
          desc="Upload a CSV as a reference schema"
        />
      </div>

      {/* Prompt input */}
      {mode === 'prompt' && (
        <Card>
          <CardContent style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-primary)', display: 'block', marginBottom: '0.5rem' }}>
                Dataset description
              </label>
              <textarea
                className="input-control"
                style={{ minHeight: '120px', resize: 'vertical', lineHeight: 1.6 }}
                placeholder="e.g. Generate 500 rows of customer data including first name, last name, email, country, and lifetime value..."
                value={prompt}
                onChange={(e) => { setPrompt(e.target.value); setError(''); }}
              />
            </div>

            {/* Quick templates */}
            <div>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                Quick templates:
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {templates.map((t) => (
                  <button
                    key={t.label}
                    onClick={() => setPrompt(t.prompt)}
                    style={{
                      padding: '0.25rem 0.75rem', fontSize: '0.8125rem', fontWeight: 500,
                      borderRadius: '999px', border: '1px solid var(--border-subtle)',
                      backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)',
                      cursor: 'pointer', transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => { (e.target as HTMLButtonElement).style.borderColor = 'var(--border-strong)'; (e.target as HTMLButtonElement).style.color = 'var(--text-primary)'; }}
                    onMouseLeave={e => { (e.target as HTMLButtonElement).style.borderColor = 'var(--border-subtle)'; (e.target as HTMLButtonElement).style.color = 'var(--text-secondary)'; }}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* File upload */}
      {mode === 'dataset' && (
        <>
          <Card>
            <CardContent style={{ padding: '1.5rem' }}>
              <div
                style={{
                  border: `2px dashed ${file ? 'var(--border-focus)' : 'var(--border-subtle)'}`,
                  borderRadius: 'var(--radius-lg)',
                  padding: '2.5rem 1.5rem',
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem',
                  cursor: 'pointer', transition: 'border-color 0.15s',
                  backgroundColor: 'var(--bg-tertiary)',
                }}
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => document.getElementById('file-upload')?.click()}
              >
                <input id="file-upload" type="file" accept=".csv,.xlsx,.xls,.json,.parquet" onChange={handleFileChange} style={{ display: 'none' }} />
                {file ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <FileText size={32} color="var(--info-color)" />
                    <div>
                      <p style={{ fontWeight: 500, color: 'var(--text-primary)', fontSize: '0.9375rem' }}>{file.name}</p>
                      <p style={{ color: 'var(--text-muted)', fontSize: '0.8125rem' }}>{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); setFile(null); }}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: '0.25rem' }}
                    >
                      <X size={18} />
                    </button>
                  </div>
                ) : (
                  <>
                    <UploadCloud size={36} color="var(--text-muted)" />
                    <div style={{ textAlign: 'center' }}>
                      <p style={{ fontWeight: 500, color: 'var(--text-primary)', fontSize: '0.9375rem' }}>
                        Click or drag file to upload
                      </p>
                      <p style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', marginTop: '0.25rem' }}>
                        CSV, XLSX, JSON, Parquet — max 100 MB
                      </p>
                    </div>
                  </>
                )}
              </div>
            </CardContent>
          </Card>

          {file && (
            <Card>
              <CardContent style={{ padding: '1.5rem' }}>
                <div>
                  <label style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-primary)', display: 'block', marginBottom: '0.5rem' }}>
                    Instructions (optional)
                  </label>
                  <textarea
                    className="input-control"
                    style={{ minHeight: '80px', resize: 'vertical', lineHeight: 1.6 }}
                    placeholder={`e.g. Generate exactly ${rows} rows based on the uploaded dataset. Focus on realistic variations...`}
                    value={prompt}
                    onChange={(e) => { setPrompt(e.target.value); setError(''); }}
                  />
                  <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                    Add custom instructions for generation, or specify "Generate exactly [number] rows" to override the default.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Settings */}
      <Card>
        <CardContent style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 500, color: 'var(--text-primary)', margin: 0 }}>
            Output settings
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <Input
              label="Number of rows"
              type="number"
              value={rows}
              onChange={(e) => setRows(Math.max(1, parseInt(e.target.value) || 100))}
              min={1}
              max={100000}
            />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
              <label className="input-label">Export format</label>
              <select
                className="input-control"
                value={format}
                onChange={(e) => setFormat(e.target.value)}
              >
                <option value="CSV">CSV</option>
                <option value="JSON">JSON (coming soon)</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Generate button */}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          onClick={handleGenerate}
          disabled={mode === 'dataset' ? !file : !prompt.trim()}
          style={{ minWidth: '160px', height: '44px' }}
        >
          Generate {rows.toLocaleString()} Rows
        </Button>
      </div>
    </div>
  );
};

const ModeCard: React.FC<{ active: boolean; onClick: () => void; icon: React.ReactNode; title: string; desc: string }> = ({ active, onClick, icon, title, desc }) => (
  <div
    onClick={onClick}
    style={{
      padding: '1.25rem', borderRadius: 'var(--radius-lg)', cursor: 'pointer',
      border: `1px solid ${active ? 'var(--border-focus)' : 'var(--border-subtle)'}`,
      backgroundColor: active ? 'var(--surface-active)' : 'var(--bg-secondary)',
      transition: 'all 0.15s',
    }}
  >
    <div style={{ color: 'var(--text-primary)', marginBottom: '0.5rem' }}>{icon}</div>
    <p style={{ fontSize: '0.9375rem', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>{title}</p>
    <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>{desc}</p>
  </div>
);

export default Generate;
