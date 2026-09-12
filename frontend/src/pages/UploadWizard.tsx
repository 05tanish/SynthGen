import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, ArrowRight, Loader, FileText, X, Database, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';
import axios from 'axios';
import { API_BASE } from '../lib/api';

const UploadWizard = () => {
  const [mode, setMode] = useState<'dataset' | 'prompt'>('dataset');
  const [file, setFile] = useState<File | null>(null);
  const [prompt, setPrompt] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (mode === 'dataset' && !file) {
      setError('Please upload a source dataset.');
      return;
    }
    if (mode === 'prompt' && !prompt.trim()) {
      setError('Please provide a generation prompt.');
      return;
    }

    setIsUploading(true);
    setError('');

    try {
      let jobId;

      if (mode === 'dataset' && file) {
        // Path A: Upload File (with optional prompt)
        const formData = new FormData();
        formData.append('file', file);
        if (prompt.trim()) {
          formData.append('prompt', prompt.trim());
        }
        
        const uploadRes = await axios.post(`${API_BASE}/datasets/upload`, formData);
        const datasetId = uploadRes.data.id;

        // Trigger generation job
        const genRes = await axios.post(`${API_BASE}/datasets/${datasetId}/generate`);
        jobId = genRes.data.job_id;
      } else {
        // Path B: Zero-Shot Prompt Generation
        const genRes = await axios.post(`${API_BASE}/datasets/generate-from-prompt`, {
          prompt: prompt.trim()
        });
        jobId = genRes.data.job_id;
      }

      // Navigate to tracker
      navigate(`/jobs/${jobId}`);
    } catch (err: any) {
      console.error(err);
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
          ? detail.map((d: any) => d.msg).join(', ')
          : 'Failed to initialize pipeline. Please try again.'
      );
      setIsUploading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="glass-panel"
      style={{ maxWidth: '640px', margin: '2rem auto' }}
    >
      <h2 style={{ textAlign: 'center', marginBottom: '1rem' }}>Configure Generation</h2>
      <p style={{ textAlign: 'center', color: 'var(--text-color)', marginBottom: '2rem', fontSize: '0.95rem' }}>
        How would you like to generate your synthetic data?
      </p>

      {/* Mode Selector */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
        <button
          onClick={() => { setMode('dataset'); setError(''); }}
          style={{
            flex: 1,
            padding: '1.25rem',
            borderRadius: '12px',
            border: `2px solid ${mode === 'dataset' ? 'var(--primary-color)' : 'var(--glass-border)'}`,
            background: mode === 'dataset' ? 'rgba(102, 252, 241, 0.1)' : 'transparent',
            color: mode === 'dataset' ? 'var(--primary-color)' : 'var(--text-color)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '0.5rem',
            cursor: 'pointer',
            transition: 'all 0.2s ease'
          }}
        >
          <Database size={28} />
          <span style={{ fontWeight: 600 }}>Enhance Dataset</span>
          <span style={{ fontSize: '0.8rem', opacity: 0.8 }}>Upload CSV/JSON</span>
        </button>
        <button
          onClick={() => { setMode('prompt'); setError(''); }}
          style={{
            flex: 1,
            padding: '1.25rem',
            borderRadius: '12px',
            border: `2px solid ${mode === 'prompt' ? 'var(--primary-color)' : 'var(--glass-border)'}`,
            background: mode === 'prompt' ? 'rgba(102, 252, 241, 0.1)' : 'transparent',
            color: mode === 'prompt' ? 'var(--primary-color)' : 'var(--text-color)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '0.5rem',
            cursor: 'pointer',
            transition: 'all 0.2s ease'
          }}
        >
          <Sparkles size={28} />
          <span style={{ fontWeight: 600 }}>From Scratch</span>
          <span style={{ fontSize: '0.8rem', opacity: 0.8 }}>Prompt Only</span>
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        {/* File Drop Zone (Only for dataset mode) */}
        {mode === 'dataset' && (
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            style={{
              border: `2px dashed ${file ? 'var(--primary-color)' : 'var(--glass-border)'}`,
              borderRadius: '12px',
              padding: '2.5rem',
              textAlign: 'center',
              transition: 'border-color 0.3s ease',
              backgroundColor: file ? 'rgba(102, 252, 241, 0.05)' : 'transparent',
              cursor: 'pointer',
            }}
            onClick={() => document.getElementById('file-upload')?.click()}
          >
            <UploadCloud size={40} color="var(--primary-color)" style={{ marginBottom: '1rem' }} />
            <h3 style={{ marginBottom: '0.5rem' }}>Upload Source Dataset (Required)</h3>
            <p style={{ color: 'var(--text-color)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
              Drag and drop your file here, or click to browse.
            </p>

            <input
              type="file"
              id="file-upload"
              style={{ display: 'none' }}
              onChange={handleFileChange}
              accept=".csv,.xlsx,.parquet,.json"
            />

            {file ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', color: 'var(--primary-color)' }}>
                <FileText size={18} />
                <span style={{ fontWeight: 600 }}>{file.name}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); setFile(null); }}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--danger-color)', display: 'flex' }}
                >
                  <X size={16} />
                </button>
              </div>
            ) : (
              <span className="btn-secondary" style={{ cursor: 'pointer' }}>Select File</span>
            )}
          </div>
        )}

        {/* Custom Prompt */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <label htmlFor="prompt" style={{ fontWeight: 600 }}>
            {mode === 'prompt' ? 'Generation Prompt (Required)' : 'Generation Prompt (Optional)'}
          </label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={
              mode === 'prompt' 
              ? "E.g., Generate realistic PII data with US formats, a 50/50 gender ratio, and some null values in the middle_name column."
              : "E.g., Preserve the original data distribution, but anonymize all PII columns."
            }
            style={{
              padding: '1rem',
              borderRadius: '8px',
              border: '1px solid var(--glass-border)',
              background: 'rgba(255, 255, 255, 0.05)',
              color: 'var(--text-color)',
              minHeight: '100px',
              resize: 'vertical',
              fontFamily: 'inherit',
              fontSize: '0.9rem',
              lineHeight: 1.6,
            }}
          />
        </div>

        {error && (
          <div style={{ color: 'var(--danger-color)', padding: '1rem', background: 'rgba(255, 75, 75, 0.1)', borderRadius: '8px', fontSize: '0.9rem' }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        <button
          className="btn-primary"
          style={{ justifyContent: 'center', padding: '1rem' }}
          onClick={handleUpload}
          disabled={
            (mode === 'dataset' && !file) || 
            (mode === 'prompt' && !prompt.trim()) || 
            isUploading
          }
        >
          {isUploading ? (
            <><Loader className="spin" size={20} /> Initializing Pipeline...</>
          ) : (
            <>Start Autonomous Generation <ArrowRight size={20} /></>
          )}
        </button>
      </div>
    </motion.div>
  );
};

export default UploadWizard;
