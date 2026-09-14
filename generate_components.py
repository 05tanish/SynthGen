import os

base_dir = "/Users/tanishjain/carrer/mainprojects/agentic ai/frontend/src/components"
ui_dir = os.path.join(base_dir, "ui")
layout_dir = os.path.join(base_dir, "layout")

os.makedirs(ui_dir, exist_ok=True)
os.makedirs(layout_dir, exist_ok=True)

button_code = """import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({ 
  children, variant = 'primary', size = 'md', isLoading, className = '', ...props 
}) => {
  const baseStyle = "inline-flex items-center justify-center font-medium rounded-md transition-colors focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed";
  
  const variants = {
    primary: "bg-white text-black hover:bg-gray-200",
    secondary: "bg-[#111111] text-white border border-[#333333] hover:bg-[#161616]",
    ghost: "bg-transparent text-gray-400 hover:text-white hover:bg-[#111111]",
    danger: "bg-red-500/10 text-red-500 hover:bg-red-500/20"
  };
  
  const sizes = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2 text-sm",
    lg: "px-6 py-3 text-base"
  };

  return (
    <button 
      className={`${baseStyle} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={isLoading || props.disabled}
      {...props}
    >
      {isLoading ? <span className="mr-2 animate-spin border-2 border-current border-t-transparent rounded-full w-4 h-4" /> : null}
      {children}
    </button>
  );
};
"""
with open(os.path.join(ui_dir, "Button.tsx"), "w") as f: f.write(button_code)

input_code = """import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input: React.FC<InputProps> = ({ label, error, className = '', ...props }) => {
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      {label && <label className="text-sm font-medium text-gray-300">{label}</label>}
      <input 
        className={`bg-[#0a0a0a] border ${error ? 'border-red-500' : 'border-[#333333]'} text-white placeholder-gray-500 px-3 py-2 rounded-md focus:outline-none focus:border-white transition-colors`}
        {...props}
      />
      {error && <span className="text-xs text-red-500">{error}</span>}
    </div>
  );
};
"""
with open(os.path.join(ui_dir, "Input.tsx"), "w") as f: f.write(input_code)

card_code = """import React from 'react';
import { motion } from 'framer-motion';

export const Card: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <div className={`bg-[#111111] border border-[#222222] rounded-xl overflow-hidden ${className}`}>
    {children}
  </div>
);

export const CardHeader: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <div className={`px-6 py-4 border-b border-[#222222] ${className}`}>
    {children}
  </div>
);

export const CardContent: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <div className={`px-6 py-4 ${className}`}>
    {children}
  </div>
);
"""
with open(os.path.join(ui_dir, "Card.tsx"), "w") as f: f.write(card_code)

badge_code = """import React from 'react';

export const Badge: React.FC<{ children: React.ReactNode; variant?: 'default' | 'success' | 'warning' | 'error' | 'outline' }> = ({ children, variant = 'default' }) => {
  const variants = {
    default: "bg-[#222222] text-gray-300",
    success: "bg-emerald-500/10 text-emerald-500",
    warning: "bg-amber-500/10 text-amber-500",
    error: "bg-red-500/10 text-red-500",
    outline: "bg-transparent border border-[#333333] text-gray-400"
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${variants[variant]}`}>
      {children}
    </span>
  );
};
"""
with open(os.path.join(ui_dir, "Badge.tsx"), "w") as f: f.write(badge_code)

spinner_code = """import React from 'react';

export const Spinner: React.FC<{ size?: 'sm' | 'md' | 'lg' }> = ({ size = 'md' }) => {
  const sizes = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-8 h-8' };
  return (
    <div className={`${sizes[size]} animate-spin border-2 border-white/20 border-t-white rounded-full`} />
  );
};
"""
with open(os.path.join(ui_dir, "Spinner.tsx"), "w") as f: f.write(spinner_code)

