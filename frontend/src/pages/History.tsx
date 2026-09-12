import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_BASE } from '../lib/api';
import { Database, Download, Eye, FileSpreadsheet, Calendar, Search } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface Dataset {
  id: number;
  name: string;
  source_type: string;
  row_count: number;
  column_count: number;
  created_at: string;
  jobs: any[]; // Or define the full type if needed
}

export default function History() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        const response = await axios.get(`${API_BASE}/v1/datasets/`);
        setDatasets(response.data);
      } catch (error) {
        console.error('Failed to fetch datasets:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDatasets();
  }, []);

  const filteredDatasets = datasets.filter(d => 
    d.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-8 animate-fade-in">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold mb-2">Generation History</h1>
          <p className="text-gray-400">View and manage your previously generated synthetic datasets.</p>
        </div>
        
        <div className="relative w-full md:w-64">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
          <input 
            type="text" 
            placeholder="Search datasets..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg focus:outline-none focus:border-[var(--primary-color)] transition-colors"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center p-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--primary-color)]"></div>
        </div>
      ) : filteredDatasets.length === 0 ? (
        <div className="glass-panel p-12 text-center flex flex-col items-center">
          <Database size={48} className="text-gray-500 mb-4" />
          <h3 className="text-xl font-semibold mb-2">No datasets found</h3>
          <p className="text-gray-400 mb-6">You haven't generated any synthetic data yet.</p>
          <button 
            onClick={() => navigate('/generate')}
            className="px-6 py-2 bg-[var(--primary-color)] text-black rounded-lg font-medium hover:bg-[var(--accent-color)] transition-colors"
          >
            Start Generating
          </button>
        </div>
      ) : (
        <div className="glass-panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/10 bg-white/5">
                  <th className="p-4 font-semibold text-sm text-gray-300">Name</th>
                  <th className="p-4 font-semibold text-sm text-gray-300">Source</th>
                  <th className="p-4 font-semibold text-sm text-gray-300">Rows x Cols</th>
                  <th className="p-4 font-semibold text-sm text-gray-300">Date Created</th>
                  <th className="p-4 font-semibold text-sm text-gray-300 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredDatasets.map(dataset => (
                  <tr key={dataset.id} className="border-b border-white/5 hover:bg-white/5 transition-colors group">
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded bg-blue-500/10 flex items-center justify-center text-blue-400">
                          <FileSpreadsheet size={16} />
                        </div>
                        <span className="font-medium truncate max-w-xs block" title={dataset.name}>
                          {dataset.name}
                        </span>
                      </div>
                    </td>
                    <td className="p-4 text-gray-400 text-sm">
                      <span className="px-2 py-1 bg-white/5 rounded text-xs capitalize border border-white/10">
                        {dataset.source_type}
                      </span>
                    </td>
                    <td className="p-4 text-gray-400 text-sm">
                      {dataset.row_count.toLocaleString()} x {dataset.column_count}
                    </td>
                    <td className="p-4 text-gray-400 text-sm">
                      <div className="flex items-center gap-1">
                        <Calendar size={14} />
                        {new Date(dataset.created_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="p-4 text-right">
                      <button 
                        onClick={() => navigate(`/dashboard`)} // Ideally link to a dataset details page or job tracker
                        className="p-2 text-gray-400 hover:text-[var(--primary-color)] transition-colors"
                        title="View Details"
                      >
                        <Eye size={18} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
