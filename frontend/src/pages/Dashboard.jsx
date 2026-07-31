import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Upload, FileText, TrendingUp, ShieldCheck, ShieldAlert, Clock, ArrowRight } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth } from '../contexts/AuthContext';
import { getErrorMessage } from '../lib/getErrorMessage';

const VERDICT_STYLES = {
  SAFE: 'text-green-400 bg-green-500/10 border-green-500/30',
  SUSPICIOUS: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  'HIGH RISK': 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  CRITICAL: 'text-red-400 bg-red-500/10 border-red-500/30',
};

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchOverview = async () => {
      try {
        // No dedicated per-user stats endpoint exists yet - same approach
        // Statistics.jsx uses: derive counts client-side from history.
        // page_size capped at 100 by the backend, so this is a most-recent
        // -100 view for very high-volume accounts; `total` is still exact.
        const response = await axios.get('/api/v1/history?page=1&page_size=100');
        const items = response.data.items || [];

        const verdictCounts = items.reduce((acc, item) => {
          const verdict = item.verdict || 'PENDING';
          acc[verdict] = (acc[verdict] || 0) + 1;
          return acc;
        }, {});
        const threats = (verdictCounts.SUSPICIOUS || 0) + (verdictCounts['HIGH RISK'] || 0) + (verdictCounts.CRITICAL || 0);
        const avgRiskScore = items.length
          ? items.reduce((sum, item) => sum + (item.risk_score || 0), 0) / items.length
          : 0;

        setStats({
          total: response.data.total || 0,
          safe: verdictCounts.SAFE || 0,
          threats,
          avgRiskScore,
        });
        setRecent(items.slice(0, 5));
      } catch (error) {
        toast.error(getErrorMessage(error, 'Failed to load dashboard'));
      } finally {
        setLoading(false);
      }
    };

    fetchOverview();
  }, []);

  const hasData = stats && stats.total > 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 pt-20 px-4 pb-8">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold text-gradient mb-2">
            Welcome back{user?.full_name ? `, ${user.full_name}` : ''}
          </h1>
          <p className="text-slate-300 text-lg">Here's a quick look at your file analysis activity</p>
        </motion.div>

        {/* Upload CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8"
        >
          <Link
            to="/upload"
            className="flex items-center justify-between gap-4 rounded-2xl p-6 bg-gradient-to-r from-blue-500/20 to-purple-500/20 border border-blue-500/30 hover:border-blue-400/50 transition-colors group"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                <Upload className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <p className="text-white font-semibold text-lg">Upload a File to Analyze</p>
                <p className="text-slate-400 text-sm">Get hashes, metadata, threat matches, and a risk score</p>
              </div>
            </div>
            <ArrowRight className="w-6 h-6 text-blue-400 flex-shrink-0 group-hover:translate-x-1 transition-transform" />
          </Link>
        </motion.div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto"></div>
          </div>
        ) : !hasData ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/20"
          >
            <div className="text-center py-12">
              <FileText className="w-16 h-16 text-slate-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">No scans yet</h3>
              <p className="text-slate-400">Upload your first file above to see your activity here</p>
            </div>
          </motion.div>
        ) : (
          <>
            {/* Quick stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="card-hover bg-white/10 backdrop-blur-lg rounded-xl p-5 border border-white/20"
              >
                <FileText className="w-6 h-6 text-blue-400 mb-2" />
                <p className="text-slate-400 text-xs">Total Scanned</p>
                <p className="text-2xl font-bold text-white">{stats.total}</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 }}
                className="card-hover bg-white/10 backdrop-blur-lg rounded-xl p-5 border border-white/20"
              >
                <TrendingUp className="w-6 h-6 text-purple-400 mb-2" />
                <p className="text-slate-400 text-xs">Avg Risk Score</p>
                <p className="text-2xl font-bold text-white">{stats.avgRiskScore.toFixed(1)}/100</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="card-hover bg-white/10 backdrop-blur-lg rounded-xl p-5 border border-white/20"
              >
                <ShieldCheck className="w-6 h-6 text-green-400 mb-2" />
                <p className="text-slate-400 text-xs">Safe Files</p>
                <p className="text-2xl font-bold text-white">{stats.safe}</p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
                className="card-hover bg-white/10 backdrop-blur-lg rounded-xl p-5 border border-white/20"
              >
                <ShieldAlert className="w-6 h-6 text-orange-400 mb-2" />
                <p className="text-slate-400 text-xs">Threats Detected</p>
                <p className="text-2xl font-bold text-white">{stats.threats}</p>
              </motion.div>
            </div>

            {/* Recent scans */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-6 border border-white/20"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Recent Scans</h3>
                <Link to="/history" className="text-sm text-blue-400 hover:text-blue-300 flex items-center gap-1">
                  View all <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
              <div className="divide-y divide-white/10">
                {recent.map((item) => (
                  <div key={item.file_id} className="py-3 flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-0">
                      <FileText className="w-5 h-5 text-slate-400 flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="text-white font-medium truncate">{item.original_name}</p>
                        <p className="text-slate-400 text-xs flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {new Date(item.upload_time).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <span className={`px-3 py-1 rounded-full border text-xs font-semibold flex-shrink-0 ${VERDICT_STYLES[item.verdict] || 'text-slate-400 bg-slate-500/10 border-slate-500/30'}`}>
                      {item.verdict || 'PENDING'}
                    </span>
                  </div>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </div>
    </div>
  );
}
