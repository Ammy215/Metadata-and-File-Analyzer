import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Users, FileText, Shield, Activity, TrendingUp, AlertTriangle, RefreshCw } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { getErrorMessage } from '../lib/getErrorMessage';

const formatStorage = (bytes) => {
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
  if (bytes >= 1024 ** 2) return `${(bytes / 1024 ** 2).toFixed(2)} MB`;
  return `${(bytes / 1024).toFixed(2)} KB`;
};

export default function AdminDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get('/api/v1/admin/dashboard/stats');
      setStats(response.data);
    } catch (err) {
      const message = getErrorMessage(err, 'Failed to load dashboard statistics');
      console.error('Failed to fetch dashboard stats:', err);
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const StatCard = ({ icon: Icon, label, value, color, trend, onClick }) => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={onClick}
      className={`card-hover bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20 ${onClick ? 'cursor-pointer hover:bg-white/20 hover:scale-105 transition-all duration-200' : ''}`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-slate-400 text-sm mb-1">{label}</p>
          <h3 className="text-3xl font-bold text-white mb-2">{value}</h3>
          {trend && (
            <div className="flex items-center gap-1 text-sm">
              <TrendingUp className="w-4 h-4 text-green-400" />
              <span className="text-green-400">{trend}</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </motion.div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 pt-20 px-4 pb-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center gap-3 mb-2">
            <Shield className="w-8 h-8 text-blue-400" />
            <h1 className="text-4xl font-bold text-gradient">Admin Dashboard</h1>
          </div>
          <p className="text-slate-300 text-lg">
            Welcome back, {user?.full_name}! Here&apos;s your system overview.
          </p>
        </motion.div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto"></div>
            <p className="text-slate-400 mt-4">Loading dashboard...</p>
          </div>
        ) : error ? (
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/20 text-center py-12">
            <AlertTriangle className="w-16 h-16 text-red-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Couldn&apos;t load dashboard</h3>
            <p className="text-slate-400 mb-6">{error}</p>
            <button
              onClick={fetchDashboardStats}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded-lg text-blue-400 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Retry
            </button>
          </div>
        ) : (
          <>
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <StatCard
                icon={Users}
                label="Total Users"
                value={stats?.users?.total ?? 0}
                color="bg-blue-500/20"
                trend={stats?.users?.new_this_week ? `+${stats.users.new_this_week} this week` : null}
                onClick={() => navigate('/admin/user-activity')}
              />
              <StatCard
                icon={FileText}
                label="Files Scanned"
                value={stats?.files?.total ?? 0}
                color="bg-purple-500/20"
                trend={stats?.files?.today ? `+${stats.files.today} today` : null}
              />
              <StatCard
                icon={Activity}
                label="Storage Used"
                value={formatStorage(stats?.storage?.used_bytes ?? 0)}
                color="bg-green-500/20"
              />
              <StatCard
                icon={AlertTriangle}
                label="Active Threats"
                value={(stats?.files?.by_verdict?.critical ?? 0) + (stats?.files?.by_verdict?.high_risk ?? 0)}
                color="bg-red-500/20"
                onClick={() => navigate('/admin/threat-analysis')}
              />
            </div>

            {/* Quick Actions */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8"
            >
              <Link
                to="/admin/users"
                className="card-hover bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20 hover:bg-white/15 transition-all group"
              >
                <Users className="w-8 h-8 text-blue-400 mb-3" />
                <h3 className="text-lg font-semibold text-white mb-2">Manage Users</h3>
                <p className="text-slate-400 text-sm">View and manage all user accounts</p>
              </Link>

              <Link
                to="/admin/files"
                className="card-hover bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20 hover:bg-white/15 transition-all group"
              >
                <FileText className="w-8 h-8 text-purple-400 mb-3" />
                <h3 className="text-lg font-semibold text-white mb-2">View Files</h3>
                <p className="text-slate-400 text-sm">Monitor all uploaded files</p>
              </Link>

              <Link
                to="/admin/audit-logs"
                className="card-hover bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20 hover:bg-white/15 transition-all group"
              >
                <Activity className="w-8 h-8 text-green-400 mb-3" />
                <h3 className="text-lg font-semibold text-white mb-2">Audit Logs</h3>
                <p className="text-slate-400 text-sm">Review system activity logs</p>
              </Link>
            </motion.div>

            {/* Activity Summary */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20"
            >
              <h2 className="text-xl font-bold text-white mb-4">Activity This Week</h2>
              {stats?.activity?.events_this_week > 0 ? (
                <div className="flex items-center gap-3 p-3 bg-white/5 rounded-lg">
                  <Activity className="w-5 h-5 text-blue-400" />
                  <p className="text-white text-sm">
                    {stats.activity.events_this_week} audit event{stats.activity.events_this_week === 1 ? '' : 's'} logged this week
                  </p>
                  <Link to="/admin/audit-logs" className="ml-auto text-blue-400 text-sm hover:text-blue-300 transition-colors">
                    View logs →
                  </Link>
                </div>
              ) : (
                <div className="text-center py-8">
                  <Activity className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                  <p className="text-slate-400">No activity this week</p>
                </div>
              )}
            </motion.div>
          </>
        )}
      </div>
    </div>
  );
}
