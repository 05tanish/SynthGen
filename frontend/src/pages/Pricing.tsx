import React from 'react';
import { Navbar } from '../components/layout/Navbar';
import { Footer } from '../components/layout/Footer';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Check } from 'lucide-react';
import { Link } from 'react-router-dom';

const Pricing: React.FC = () => {
  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      
      <main className="flex-1 w-full" style={{ paddingTop: '100px' }}>
        <section className="flex flex-col items-center justify-center text-center px-4" style={{ padding: '6rem 0' }}>
          <h1 style={{ fontSize: '3.5rem', marginBottom: '1rem' }} className="text-gradient">
            Simple, predictable pricing
          </h1>
          <p style={{ fontSize: '1.125rem', color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto 4rem auto' }}>
            Whether you're a solo developer or an enterprise team, we have a plan for your data needs.
          </p>
          
          <div className="flex flex-col md:flex-row gap-6 max-w-5xl mx-auto w-full px-4 justify-center">
            
            {/* Free Tier */}
            <Card className="flex-1 max-w-[320px] text-left">
              <div style={{ padding: '2rem' }} className="flex flex-col h-full">
                <h3 style={{ fontSize: '1.25rem', margin: '0 0 0.5rem 0' }}>Free</h3>
                <div style={{ fontSize: '2.5rem', fontWeight: 700, margin: '0 0 1rem 0' }}>$0<span style={{ fontSize: '1rem', color: 'var(--text-secondary)', fontWeight: 400 }}>/mo</span></div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '2rem' }}>For experimentation and simple schemas.</p>
                
                <ul className="flex flex-col gap-3 mb-8 flex-1" style={{ listStyle: 'none', padding: 0 }}>
                  <FeatureItem text="100,000 rows / month" />
                  <FeatureItem text="Basic schemas" />
                  <FeatureItem text="CSV export" />
                  <FeatureItem text="Community support" />
                </ul>
                
                <Link to="/register" className="w-full">
                  <Button variant="secondary" className="w-full">Start Free</Button>
                </Link>
              </div>
            </Card>

            {/* Pro Tier */}
            <Card className="flex-1 max-w-[320px] text-left" style={{ borderColor: 'var(--text-primary)', transform: 'scale(1.05)', zIndex: 10 }}>
              <div style={{ padding: '2rem' }} className="flex flex-col h-full">
                <div className="flex justify-between items-center mb-2">
                  <h3 style={{ fontSize: '1.25rem', margin: 0 }}>Pro</h3>
                  <span className="badge badge-outline" style={{ borderColor: 'var(--text-primary)', color: 'var(--text-primary)' }}>Popular</span>
                </div>
                <div style={{ fontSize: '2.5rem', fontWeight: 700, margin: '0 0 1rem 0' }}>$49<span style={{ fontSize: '1rem', color: 'var(--text-secondary)', fontWeight: 400 }}>/mo</span></div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '2rem' }}>For professional developers and analysts.</p>
                
                <ul className="flex flex-col gap-3 mb-8 flex-1" style={{ listStyle: 'none', padding: 0 }}>
                  <FeatureItem text="10,000,000 rows / month" />
                  <FeatureItem text="Advanced relationships" />
                  <FeatureItem text="JSON & Parquet export" />
                  <FeatureItem text="API access" />
                  <FeatureItem text="Priority support" />
                </ul>
                
                <Link to="/register" className="w-full">
                  <Button variant="primary" className="w-full">Start Pro</Button>
                </Link>
              </div>
            </Card>

            {/* Team Tier */}
            <Card className="flex-1 max-w-[320px] text-left">
              <div style={{ padding: '2rem' }} className="flex flex-col h-full">
                <h3 style={{ fontSize: '1.25rem', margin: '0 0 0.5rem 0' }}>Team</h3>
                <div style={{ fontSize: '2.5rem', fontWeight: 700, margin: '0 0 1rem 0' }}>$199<span style={{ fontSize: '1rem', color: 'var(--text-secondary)', fontWeight: 400 }}>/mo</span></div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '2rem' }}>For scaling teams needing shared workspaces.</p>
                
                <ul className="flex flex-col gap-3 mb-8 flex-1" style={{ listStyle: 'none', padding: 0 }}>
                  <FeatureItem text="Unlimited generation" />
                  <FeatureItem text="Custom enterprise schemas" />
                  <FeatureItem text="Direct DB connection" />
                  <FeatureItem text="Team workspaces" />
                  <FeatureItem text="Dedicated support" />
                </ul>
                
                <Link to="/contact" className="w-full">
                  <Button variant="secondary" className="w-full">Contact Sales</Button>
                </Link>
              </div>
            </Card>

          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
};

const FeatureItem: React.FC<{ text: string }> = ({ text }) => (
  <li className="flex items-center gap-3" style={{ fontSize: '0.875rem', color: 'var(--text-primary)' }}>
    <Check size={16} color="var(--success-color)" />
    {text}
  </li>
);

export default Pricing;
