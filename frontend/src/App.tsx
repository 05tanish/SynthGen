import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AppLayout } from './components/layout/AppLayout';

// Public Pages
import Home from './pages/Home';
import Pricing from './pages/Pricing';
import Login from './pages/Login';
import Register from './pages/Register';

// App Pages
import Dashboard from './pages/Dashboard';
import Generate from './pages/UploadWizard';
import JobTracker from './pages/JobTracker';
import History from './pages/History';
import Profile from './pages/Profile';
import DatasetDetail from './pages/DatasetDetail';
import Templates from './pages/Templates';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/docs" element={<Home />} />

          {/* Protected App Routes */}
          <Route path="/app" element={<AppLayout />}>
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="generate" element={<Generate />} />
            <Route path="templates" element={<Templates />} />
            <Route path="datasets" element={<History />} />
            <Route path="datasets/:id" element={<DatasetDetail />} />
            <Route path="jobs/:jobId" element={<JobTracker />} />
            <Route path="settings" element={<Profile />} />
            {/* Redirect legacy routes */}
            <Route path="history" element={<History />} />
            <Route path="api-keys" element={<Profile />} />
            <Route path="usage" element={<Profile />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
