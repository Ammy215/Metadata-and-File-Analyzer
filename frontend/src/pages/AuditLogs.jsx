import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Activity, Search, Filter, Calendar, User, FileText, Shield, AlertTriangle } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [daysFilter, setDaysFilter] = useState(7);

  // fetchLogs intentionally omitted from deps - see AuthContext.jsx for
  // why (new reference every render; this should only re-run on filter change).
  useEffect(() => {
    fetchLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [daysFilter, actionFilter]);

  const fetchLogs = async () => {
    try {
      let url = `/api/v1/admin/audit-logs?days=${daysFilter}&limit=200`;
      if (actionFilter) {
        url += `&action=${actionFilter}`;
      }
      const response = await axios.get(url);
      setLogs(response.data || []);
    } catch (error) {
      console.error('Failed to fetch audit logs:', error);
      toast.error('Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  const filteredLogs = logs.filter(log => {
    const searchLower = searchTerm.toLowerCase();
    return (
      log.action?.toLowerCase().includes(searchLower) ||
      log.details?.toLowerCase().includes(searchLower) ||
      log.ip_address?.toLowerCase().includes(searchLower)
    );
  });

  const getActionIcon = (action) => {
    const icons = {
      'LOGIN': <User className="w-4 h-4 text-green-400" />,
      'LOGOUT': <User className="w-4 h-4 text-slate-400" />,
      'REGISTER': <Shield className="w-4 h-4 text-blue-400" />,
      'FILE_UPLOAD': <FileText className="w-4 h-4 text-purple-400" />,
      'FILE_DELETE': <FileText className="w-4 h-4 text-red-400" />,
      'USER_UPDATE': <User className="w-4 h-4 text-yellow-400" />,
      'USER_DELETE': <User className="w-4 h-4 text-red-400" />,
      'USER_BAN': <AlertTriangle className="w-4 h-4 text-orange-400" />,
    };
    return icons[action] || <Activity className="w-4 h-4 text-slate-400" />;
  };

  const getActionBadge = (action) => {
    const badges = {
      'LOGIN': 'bg-green-500/20 text-green-400 border-green-500/30',
      'LOGOUT': 'bg-slate-500/20 text-slate-400 border-slate-500/30',
      'REGISTER': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      'FILE_UPLOAD': 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      'FILE_DELETE': 'bg-red-500/20 text-red-400 border-red-500/30',
      'USER_UPDATE': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      'USER_DELETE': 'bg-red-500/20 text-red-400 border-red-500/30',
      'USER_BAN': 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    };
    return badges[action] || 'bg-slate-500/20 text-slate-400 border-slate-500/30';
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="pt-20 px-4 pb-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
          >
            <div className="flex items-center gap-3 mb-2">
              <Activity className="w-8 h-8 text-green-400" />
              <h1 className="text-4xl font-bold text-gradient">Audit Logs</h1>
            </div>
            <p className="text-slate-300 text-lg">
              Track all system activity and user actions
            </p>
          </motion.div>

          {/* Filters */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="mb-6 grid grid-cols-1 md:grid-cols-3 gap-4"
          >
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                placeholder="Search logs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-12 pr-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>

            <div className="relative">
              <Filter className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <select
                value={actionFilter}
                onChange={(e) => setActionFilter(e.target.value)}
                className="w-full pl-12 pr-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500 appearance-none cursor-pointer"
              >
                <option value="">All Actions</option>
                <option value="LOGIN">Login</option>
                <option value="LOGOUT">Logout</option>
                <option value="REGISTER">Register</option>
                <option value="FILE_UPLOAD">File Upload</option>
                <option value="FILE_DELETE">File Delete</option>
                <option value="USER_UPDATE">User Update</option>
                <option value="USER_DELETE">User Delete</option>
                <option value="USER_BAN">User Ban</option>
              </select>
            </div>

            <div className="relative">
              <Calendar className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <select
                value={daysFilter}
                onChange={(e) => setDaysFilter(Number(e.target.value))}
                className="w-full pl-12 pr-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500 appearance-none cursor-pointer"
              >
                <option value="1">Last 24 Hours</option>
                <option value="7">Last 7 Days</option>
                <option value="30">Last 30 Days</option>
                <option value="90">Last 90 Days</option>
              </select>
            </div>
          </motion.div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20">
              <p className="text-slate-400 text-sm">Total Events</p>
              <p className="text-3xl font-bold text-white">{logs.length}</p>
            </div>
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20">
              <p className="text-slate-400 text-sm">Logins</p>
              <p className="text-3xl font-bold text-green-400">
                {logs.filter(l => l.action === 'LOGIN').length}
              </p>
            </div>
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20">
              <p className="text-slate-400 text-sm">File Actions</p>
              <p className="text-3xl font-bold text-purple-400">
                {logs.filter(l => l.action?.includes('FILE')).length}
              </p>
            </div>
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20">
              <p className="text-slate-400 text-sm">Admin Actions</p>
              <p className="text-3xl font-bold text-yellow-400">
                {logs.filter(l => l.action?.includes('USER') && l.action !== 'LOGIN' && l.action !== 'LOGOUT').length}
              </p>
            </div>
          </div>

          {/* Logs Timeline */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="bg-white/10 backdrop-blur-lg rounded-xl border border-white/20 overflow-hidden"
          >
            {loading ? (
              <div className="text-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto"></div>
                <p className="text-slate-400 mt-4">Loading audit logs...</p>
              </div>
            ) : filteredLogs.length === 0 ? (
              <div className="text-center py-12">
                <Activity className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <p className="text-slate-400">No audit logs found</p>
              </div>
            ) : (
              <div className="p-6">
                <div className="space-y-4">
                  {filteredLogs.map((log, index) => (
                    <motion.div
                      key={log.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.02 }}
                      className="flex items-start gap-4 p-4 bg-white/5 rounded-lg border border-white/10 hover:bg-white/10 transition-colors"
                    >
                      {/* Icon */}
                      <div className={`p-3 rounded-lg border ${getActionBadge(log.action)}`}>
                        {getActionIcon(log.action)}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-2">
                          <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${getActionBadge(log.action)}`}>
                            {log.action?.replace('_', ' ')}
                          </span>
                          <span className="text-slate-400 text-sm">
                            {formatDate(log.timestamp)}
                          </span>
                        </div>
                        
                        <p className="text-white font-medium mb-1">
                          {log.details || 'No details available'}
                        </p>
                        
                        <div className="flex items-center gap-4 text-sm text-slate-400">
                          {log.user_id && (
                            <span className="flex items-center gap-1">
                              <User className="w-3 h-3" />
                              User ID: {log.user_id.slice(0, 8)}...
                            </span>
                          )}
                          {log.ip_address && (
                            <span>
                              IP: {log.ip_address}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Status Indicator */}
                      <div className={`w-2 h-2 rounded-full ${
                        log.action?.includes('DELETE') || log.action?.includes('BAN') 
                          ? 'bg-red-400' 
                          : log.action === 'LOGIN' 
                          ? 'bg-green-400'
                          : 'bg-blue-400'
                      }`} />
                    </motion.div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        </div>
      </div>
  );
}
