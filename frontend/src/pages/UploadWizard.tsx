import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, ArrowRight, Loader, FileText, X } from 'lucide-react';
import { motion } from 'framer-motion';
import axios from 'axios';
import { API_BASE } from '../lib/api';

const UploadWizard = () => {
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
    if (!file && !prompt.trim()) {
      setError('Please either upload a seed file or provide a generation prompt.');
      return;
    }

    setIsUploading(true);
    setError('');

    try {
      let jobId;

      if (file) {
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
      <h2 style={{ textAlign: 'center', marginBottom: '2rem' }}>Configure Generation</h2>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        {/* File Drop Zone */}
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          style={{
            border: `2px dashed ${file ? 'var(--primary-color)' : 'var(--glass-border)'}`,
            borderRadius: '12px',
            padding: '3rem',
            textAlign: 'center',
            transition: 'border-color 0.3s ease',
            backgroundColor: file ? 'rgba(102, 252, 241, 0.05)' : 'transparent',
            cursor: 'pointer',
          }}
          onClick={() => document.getElementById('file-upload')?.click()}
        >
          <UploadCloud size={48} color="var(--primary-color)" style={{ marginBottom: '1rem' }} />
          <h3>Upload Source Dataset (Optional)</h3>
          <p style={{ color: 'var(--text-color)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
            Leave blank if you want the AI to generate data purely from your prompt below.
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

        {/* Custom Prompt */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <label htmlFor="prompt" style={{ fontWeight: 600 }}>
            Generation Prompt <span style={{ color: 'var(--text-color)', fontWeight: 400 }}>(Required if no file uploaded)</span>
          </label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="E.g., Generate realistic PII data with US formats, a 50/50 gender ratio, and some null values in the middle_name column."
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
          disabled={(!file && !prompt.trim()) || isUploading}
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
