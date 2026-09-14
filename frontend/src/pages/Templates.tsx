import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_BASE } from '../lib/api';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Spinner } from '../components/ui/Spinner';
import { Layers, ArrowRight } from 'lucide-react';

interface Template {
  id: number;
  name: string;
  description: string;
  complexity?: string;
  use_case?: string;
  prompt?: string;
}

const DEFAULT_TEMPLATES: Template[] = [
  { id: 1, name: 'Customer Data', description: 'Realistic customer profiles for CRM testing', complexity: 'Low', use_case: 'CRM / Analytics', prompt: 'Generate a customer dataset with first name, last name, email, phone number, country, city, registration date, subscription plan, and lifetime value.' },
  { id: 2, name: 'E-commerce Orders', description: 'Transaction records for analytics pipelines', complexity: 'Medium', use_case: 'E-commerce / Analytics', prompt: 'Generate e-commerce order records with order ID, product name, category, brand, unit price, quantity, discount, total, payment method, order date, and shipping status.' },
  { id: 3, name: 'Employee Records', description: 'HR datasets for workforce analytics', complexity: 'Low', use_case: 'HR / Payroll', prompt: 'Generate employee records with employee ID, full name, department, job title, hire date, salary, performance rating, manager name, and employment status.' },
  { id: 4, name: 'Healthcare Patients', description: 'Patient data for medical ML models', complexity: 'High', use_case: 'Healthcare / ML', prompt: 'Generate healthcare patient records with patient ID, age, gender, blood type, diagnosis, medication, dosage, doctor name, visit date, and hospital name.' },
  { id: 5, name: 'Financial Transactions', description: 'Bank transaction logs for fraud detection', complexity: 'Medium', use_case: 'FinTech / Fraud Detection', prompt: 'Generate financial transaction records with transaction ID, account number, transaction type, amount, merchant name, category, date, location, and fraud flag.' },
  { id: 6, name: 'Product Catalog', description: 'Product listings for e-commerce testing', complexity: 'Low', use_case: 'E-commerce / Catalog', prompt: 'Generate a product catalog with product ID, name, category, subcategory, brand, SKU, price, stock quantity, rating, and availability status.' },
  { id: 7, name: 'IoT Sensor Data', description: 'Time-series sensor readings for ML', complexity: 'High', use_case: 'IoT / ML', prompt: 'Generate IoT sensor time-series data with device ID, sensor type, timestamp, temperature, humidity, pressure, battery level, and signal strength.' },
  { id: 8, name: 'User Activity Logs', description: 'Web/app event logs for behavioral analytics', complexity: 'Medium', use_case: 'Analytics / Product', prompt: 'Generate user activity logs with user ID, session ID, event type, page URL, timestamp, device type, browser, country, and session duration.' },
];

const COMPLEXITY_COLORS: Record<string, string> = {
  Low: 'var(--success-color)',
  Medium: 'var(--warning-color)',
  High: 'var(--error-color)',
};

const Templates: React.FC = () => {
  const [templates, setTemplates] = useState<Template[]>(DEFAULT_TEMPLATES);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      try {
        const token = localStorage.getItem('token');
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        const res = await axios.get(`${API_BASE}/templates`);
        if (res.data && res.data.length > 0) setTemplates(res.data);
      } catch { /* use defaults */ } finally { setIsLoading(false); }
    };
    load();
  }, []);

  const handleUseTemplate = (template: Template) => {
    navigate('/app/generate', { state: { prompt: template.prompt || template.description, name: template.name } });
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1000px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.375rem' }}>
          Templates
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9375rem' }}>
          Start with a pre-built template to generate your dataset instantly.
        </p>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}><Spinner size="lg" /></div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
          {templates.map((t) => (
            <Card key={t.id} style={{ display: 'flex', flexDirection: 'column', transition: 'border-color 0.15s' }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--border-focus)')}
              onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border-subtle)')}>
              <CardContent style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem', flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{
                    width: '40px', height: '40px', borderRadius: 'var(--radius-md)',
                    backgroundColor: 'var(--bg-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <Layers size={18} color="var(--text-primary)" />
                  </div>
                  {t.complexity && (
                    <span style={{ fontSize: '0.75rem', fontWeight: 500, color: COMPLEXITY_COLORS[t.complexity] || 'var(--text-muted)', letterSpacing: '0.025em' }}>
                      {t.complexity}
                    </span>
                  )}
                </div>

                <div style={{ flex: 1 }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.375rem' }}>{t.name}</h3>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.55 }}>{t.description}</p>
                </div>

                {t.use_case && (
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', letterSpacing: '0.025em', textTransform: 'uppercase' }}>{t.use_case}</p>
                )}

                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleUseTemplate(t)}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', alignSelf: 'flex-start' }}
                >
                  Use Template <ArrowRight size={14} />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default Templates;
