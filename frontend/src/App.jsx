import { Routes, Route, Navigate } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { useAuth } from './contexts/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import VerifyOtp from './pages/VerifyOtp';
import AdminDashboard from './pages/AdminDashboard';
import AdminUsers from './pages/AdminUsers';
import AdminFiles from './pages/AdminFiles';
import AuditLogs from './pages/AuditLogs';
import UserActivity from './pages/UserActivity';
import ThreatAnalysis from './pages/ThreatAnalysis';
import TopBar from './components/layout/TopBar';
import UploadAnalyze from './pages/UploadAnalyze';
import Dashboard from './pages/Dashboard';
import ScanHistory from './pages/ScanHistory';
import Statistics from './pages/Statistics';
import About from './pages/About';
import NotFound from './pages/NotFound';

// Protected Route Component
function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }
  
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

// Admin Route Component - requires an authenticated admin user
function AdminRoute({ children }) {
  const { isAuthenticated, isAdmin, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return isAdmin() ? children : <Navigate to="/dashboard" replace />;
}

// Public Route (redirect to dashboard if already logged in)
function PublicRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }
  
  return isAuthenticated ? <Navigate to="/dashboard" replace /> : children;
}

// Dashboard Route - admins get the admin console overview, regular users
// get a lightweight personal overview (recent scans, quick stats, upload CTA)
function DashboardRoute() {
  const { isAdmin } = useAuth();

  return (
    <>
      <TopBar />
      {isAdmin() ? <AdminDashboard /> : <Dashboard />}
    </>
  );
}

function App() {
  return (
    <AnimatePresence mode="wait">
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />
        <Route path="/verify-otp" element={<PublicRoute><VerifyOtp /></PublicRoute>} />
        
        {/* Protected Routes */}
        <Route path="/" element={<ProtectedRoute><Navigate to="/dashboard" replace /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><DashboardRoute /></ProtectedRoute>} />
        <Route path="/upload" element={
          <ProtectedRoute>
            <TopBar />
            <UploadAnalyze />
          </ProtectedRoute>
        } />
        <Route path="/history" element={
          <ProtectedRoute>
            <TopBar />
            <ScanHistory />
          </ProtectedRoute>
        } />
        <Route path="/statistics" element={
          <ProtectedRoute>
            <TopBar />
            <Statistics />
          </ProtectedRoute>
        } />
        <Route path="/about" element={
          <ProtectedRoute>
            <TopBar />
            <About />
          </ProtectedRoute>
        } />
        
        {/* Admin Routes */}
        <Route path="/admin/users" element={
          <AdminRoute>
            <AdminUsers />
          </AdminRoute>
        } />
        <Route path="/admin/files" element={
          <AdminRoute>
            <AdminFiles />
          </AdminRoute>
        } />
        <Route path="/admin/audit-logs" element={
          <AdminRoute>
            <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
              <TopBar />
              <AuditLogs />
            </div>
          </AdminRoute>
        } />
        <Route path="/admin/user-activity" element={
          <AdminRoute>
            <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
              <TopBar />
              <UserActivity />
            </div>
          </AdminRoute>
        } />
        <Route path="/admin/threat-analysis" element={
          <AdminRoute>
            <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
              <TopBar />
              <ThreatAnalysis />
            </div>
          </AdminRoute>
        } />

        {/* Catch-all */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </AnimatePresence>
  );
}

export default App;
