import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { BarChart3, TrendingUp, ShieldCheck, ShieldAlert, FileText } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import { getErrorMessage } from '../lib/getErrorMessage';

export default function Statistics() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        // No dedicated per-user stats endpoint exists yet - computed here
        // from the same history data ScanHistory shows. page_size is capped
        // at 100 by the backend (history.py), so for users with more than
        // 100 analyzed files this is a most-recent-100 overview, not exact -
        // `total` below still reflects the true full count.
        const response = await axios.get('/api/v1/history?page=1&page_size=100');
        const items = response.data.items || [];

        const verdictCounts = items.reduce((acc, item) => {
          const verdict = item.verdict || 'PENDING';
          acc[verdict] = (acc[verdict] || 0) + 1;
          return acc;
        }, {});

        const avgRiskScore = items.length
          ? items.reduce((sum, item) => sum + (item.risk_score || 0), 0) / items.length
          : 0;

        setStats({
          total: response.data.total || 0,
          verdictCounts,
          avgRiskScore,
        });
      } catch (error) {
        toast.error(getErrorMessage(error, 'Failed to load statistics'));
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  const hasData = stats && stats.total > 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 pt-20 px-4 pb-8">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl font-bold text-gradient mb-4">Statistics</h1>
          <p className="text-slate-300 text-lg">
            View your analysis statistics and insights
          </p>
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
              <BarChart3 className="w-16 h-16 text-slate-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">No data yet</h3>
              <p className="text-slate-400">Statistics will appear after you analyze some files</p>
            </div>
          </motion.div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="card-hover bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20"
            >
              <FileText className="w-8 h-8 text-blue-400 mb-3" />
              <p className="text-slate-400 text-sm">Total Files Scanned</p>
              <p className="text-3xl font-bold text-white">{stats.total}</p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="card-hover bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20"
            >
              <TrendingUp className="w-8 h-8 text-purple-400 mb-3" />
              <p className="text-slate-400 text-sm">Average Risk Score</p>
              <p className="text-3xl font-bold text-white">{stats.avgRiskScore.toFixed(1)}/100</p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="card-hover bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20"
            >
              <ShieldCheck className="w-8 h-8 text-green-400 mb-3" />
              <p className="text-slate-400 text-sm">Safe Files</p>
              <p className="text-3xl font-bold text-white">{stats.verdictCounts.SAFE || 0}</p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="md:col-span-3 bg-white/10 backdrop-blur-lg rounded-2xl p-6 border border-white/20"
            >
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-orange-400" />
                Verdict Breakdown
              </h3>
              <div className="space-y-2">
                {Object.entries(stats.verdictCounts).map(([verdict, count]) => (
                  <div key={verdict} className="flex justify-between text-sm">
                    <span className={`text-slate-300 ${verdict === 'CRITICAL' ? 'text-red-400 font-semibold' : ''}`}>
                      {verdict}
                    </span>
                    <span className="text-white font-medium">{count}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </div>
  );
}
