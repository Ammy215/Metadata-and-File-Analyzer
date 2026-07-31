import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Clock, FileText, RefreshCw } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import { getErrorMessage } from '../lib/getErrorMessage';

const VERDICT_STYLES = {
  SAFE: 'text-green-400 bg-green-500/10 border-green-500/30',
  SUSPICIOUS: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  'HIGH RISK': 'text-orange-400 bg-orange-500/10 border-orange-500/30 glow-amber',
  CRITICAL: 'text-red-400 bg-red-500/10 border-red-500/30 pulse-critical glow-red',
};

export default function ScanHistory() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchHistory = async () => {
    try {
      const response = await axios.get('/api/v1/history?page=1&page_size=50');
      setItems(response.data.items || []);
      setTotal(response.data.total || 0);
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to load scan history'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 pt-20 px-4 pb-8">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-12"
        >
          <div>
            <h1 className="text-4xl font-bold text-gradient mb-4">Scan History</h1>
            <p className="text-slate-300 text-lg">
              View all your previously analyzed files ({total} total)
            </p>
          </div>
          <button
            onClick={() => { setLoading(true); fetchHistory(); }}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded-lg text-blue-400 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/20"
        >
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto"></div>
            </div>
          ) : items.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-16 h-16 text-slate-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">No scans yet</h3>
              <p className="text-slate-400">Upload your first file to see it here</p>
            </div>
          ) : (
            <div className="divide-y divide-white/10">
              {items.map((item) => (
                <div key={item.file_id} className="py-4 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <FileText className="w-5 h-5 text-slate-400" />
                    <div>
                      <p className="text-white font-medium">{item.original_name}</p>
                      <p className="text-slate-400 text-sm flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(item.upload_time).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-white font-medium">{item.risk_score}/100</span>
                    <span className={`px-3 py-1 rounded-full border text-sm font-semibold ${VERDICT_STYLES[item.verdict] || 'text-slate-400 bg-slate-500/10 border-slate-500/30'}`}>
                      {item.verdict || 'PENDING'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
