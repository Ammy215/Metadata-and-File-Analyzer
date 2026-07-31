import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FileText, Search, Trash2, Eye, Filter } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import TopBar from '../components/layout/TopBar';
import { getErrorMessage } from '../lib/getErrorMessage';

export default function AdminFiles() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [verdictFilter, setVerdictFilter] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);

  // fetchFiles intentionally omitted from deps - see AuthContext.jsx for
  // why (new reference every render; this should only re-run on filter change).
  useEffect(() => {
    fetchFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [verdictFilter]);

  const fetchFiles = async () => {
    try {
      setLoading(true);
      let url = '/api/v1/admin/files?limit=100';
      if (verdictFilter) {
        url += `&verdict=${verdictFilter}`;
      }
      console.log('Fetching files from:', url);
      const response = await axios.get(url);
      console.log('Files response:', response.data);
      
      // Backend returns array directly, not wrapped in object
      const filesData = Array.isArray(response.data) ? response.data : [];
      setFiles(filesData);
      
      if (filesData.length === 0) {
        console.log('No files found in database');
      }
    } catch (error) {
      console.error('Failed to fetch files:', error);
      console.error('Error response:', error.response?.data);
      console.error('Error status:', error.response?.status);
      
      // More specific error messages
      if (error.response?.status === 401) {
        toast.error('Session expired. Please login again.');
      } else if (error.response?.status === 403) {
        toast.error('Access denied. Admin privileges required.');
      } else {
        toast.error(`Failed to load files: ${getErrorMessage(error, error.message)}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteFile = async (fileId) => {
    if (!confirm('Are you sure you want to DELETE this file? This cannot be undone!')) return;
    
    try {
      await axios.delete(`/api/v1/admin/files/${fileId}`);
      toast.success('File deleted successfully');
      fetchFiles();
    } catch (error) {
      toast.error('Failed to delete file');
    }
  };

  const filteredFiles = files.filter(file =>
    file.original_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    file.mime_type?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getVerdictBadge = (verdict) => {
    const badges = {
      'SAFE': { color: 'bg-green-500/20 text-green-400 border-green-500/30', icon: '✓' },
      'SUSPICIOUS': { color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', icon: '⚠' },
      'HIGH RISK': { color: 'bg-orange-500/20 text-orange-400 border-orange-500/30 glow-amber', icon: '⚠' },
      'CRITICAL': { color: 'bg-red-500/20 text-red-400 border-red-500/30 pulse-critical glow-red', icon: '✕' },
    };
    return badges[verdict] || badges.SAFE;
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <TopBar />
      <div className="pt-20 px-4 pb-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8"
          >
            <div className="flex items-center gap-3 mb-2">
              <FileText className="w-8 h-8 text-purple-400" />
              <h1 className="text-4xl font-bold text-gradient">File Management</h1>
            </div>
            <p className="text-slate-300 text-lg">
              View and manage all uploaded files across all users
            </p>
          </motion.div>

          {/* Filters */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-4"
          >
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                placeholder="Search files by name or type..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-12 pr-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div className="relative">
              <Filter className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <select
                value={verdictFilter}
                onChange={(e) => setVerdictFilter(e.target.value)}
                className="w-full pl-12 pr-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500 appearance-none cursor-pointer"
              >
                <option value="">All Verdicts</option>
                <option value="SAFE">Safe</option>
                <option value="SUSPICIOUS">Suspicious</option>
                <option value="HIGH RISK">High Risk</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>
          </motion.div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20">
              <p className="text-slate-400 text-sm">Total Files</p>
              <p className="text-3xl font-bold text-white">{files.length}</p>
            </div>
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20">
              <p className="text-slate-400 text-sm">Safe</p>
              <p className="text-3xl font-bold text-green-400">
                {files.filter(f => f.verdict === 'SAFE').length}
              </p>
            </div>
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20">
              <p className="text-slate-400 text-sm">Suspicious</p>
              <p className="text-3xl font-bold text-yellow-400">
                {files.filter(f => f.verdict === 'SUSPICIOUS').length}
              </p>
            </div>
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20">
              <p className="text-slate-400 text-sm">High Risk</p>
              <p className="text-3xl font-bold text-orange-400">
                {files.filter(f => f.verdict === 'HIGH RISK').length}
              </p>
            </div>
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20">
              <p className="text-slate-400 text-sm">Critical</p>
              <p className="text-3xl font-bold text-red-400">
                {files.filter(f => f.verdict === 'CRITICAL').length}
              </p>
            </div>
          </div>

          {/* Files Table */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="bg-white/10 backdrop-blur-lg rounded-xl border border-white/20 overflow-hidden"
          >
            {loading ? (
              <div className="text-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto"></div>
                <p className="text-slate-400 mt-4">Loading files...</p>
              </div>
            ) : filteredFiles.length === 0 ? (
              <div className="text-center py-12">
                <FileText className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <p className="text-slate-400">No files found</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-white/5 border-b border-white/10">
                    <tr>
                      <th className="text-left px-6 py-4 text-sm font-semibold text-slate-300">File Name</th>
                      <th className="text-left px-6 py-4 text-sm font-semibold text-slate-300">Type</th>
                      <th className="text-left px-6 py-4 text-sm font-semibold text-slate-300">Size</th>
                      <th className="text-left px-6 py-4 text-sm font-semibold text-slate-300">Verdict</th>
                      <th className="text-left px-6 py-4 text-sm font-semibold text-slate-300">Risk Score</th>
                      <th className="text-left px-6 py-4 text-sm font-semibold text-slate-300">Uploaded</th>
                      <th className="text-right px-6 py-4 text-sm font-semibold text-slate-300">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredFiles.map((file, index) => {
                      const badge = getVerdictBadge(file.verdict);
                      return (
                        <motion.tr
                          key={file.id}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: index * 0.05 }}
                          className="border-b border-white/10 hover:bg-white/5 transition-colors"
                        >
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-3">
                              <FileText className="w-5 h-5 text-purple-400" />
                              <span className="text-white font-medium truncate max-w-xs">
                                {file.original_name}
                              </span>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <span className="text-slate-400 text-sm">{file.mime_type}</span>
                          </td>
                          <td className="px-6 py-4">
                            <span className="text-slate-300">{formatBytes(file.size_bytes)}</span>
                          </td>
                          <td className="px-6 py-4">
                            <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium border ${badge.color}`}>
                              {badge.icon} {file.verdict}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-2">
                              <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                                <div
                                  className={`h-full transition-all ${
                                    file.risk_score >= 75 ? 'bg-red-500' :
                                    file.risk_score >= 50 ? 'bg-orange-500' :
                                    file.risk_score >= 25 ? 'bg-yellow-500' :
                                    'bg-green-500'
                                  }`}
                                  style={{ width: `${file.risk_score}%` }}
                                />
                              </div>
                              <span className="text-slate-300 text-sm font-medium w-10">
                                {file.risk_score}
                              </span>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <span className="text-slate-400 text-sm">
                              {formatDate(file.upload_time)}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => setSelectedFile(file)}
                                className="p-2 hover:bg-white/10 rounded-lg transition-colors group"
                                title="View Details"
                              >
                                <Eye className="w-4 h-4 text-slate-400 group-hover:text-purple-400" />
                              </button>
                              
                              <button
                                onClick={() => handleDeleteFile(file.id)}
                                className="p-2 hover:bg-red-500/10 rounded-lg transition-colors group"
                                title="Delete File"
                              >
                                <Trash2 className="w-4 h-4 text-slate-400 group-hover:text-red-400" />
                              </button>
                            </div>
                          </td>
                        </motion.tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </motion.div>

          {/* File Detail Modal */}
          {selectedFile && (
            <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-slate-800 rounded-xl border border-white/20 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-6">
                    <div>
                      <h2 className="text-2xl font-bold text-white mb-2">File Details</h2>
                      <p className="text-slate-400">Complete information about this file</p>
                    </div>
                    <button
                      onClick={() => setSelectedFile(null)}
                      className="text-slate-400 hover:text-white"
                    >
                      ✕
                    </button>
                  </div>

                  <div className="space-y-4">
                    <div className="p-4 bg-white/5 rounded-lg">
                      <p className="text-slate-400 text-sm mb-1">File Name</p>
                      <p className="text-white font-medium">{selectedFile.original_name}</p>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 bg-white/5 rounded-lg">
                        <p className="text-slate-400 text-sm mb-1">File Type</p>
                        <p className="text-white font-medium">{selectedFile.mime_type}</p>
                      </div>
                      <div className="p-4 bg-white/5 rounded-lg">
                        <p className="text-slate-400 text-sm mb-1">Size</p>
                        <p className="text-white font-medium">{formatBytes(selectedFile.size_bytes)}</p>
                      </div>
                      <div className="p-4 bg-white/5 rounded-lg">
                        <p className="text-slate-400 text-sm mb-1">Verdict</p>
                        <p className={`font-medium ${
                          selectedFile.verdict === 'SAFE' ? 'text-green-400' :
                          selectedFile.verdict === 'SUSPICIOUS' ? 'text-yellow-400' :
                          selectedFile.verdict === 'HIGH RISK' ? 'text-orange-400' :
                          'text-red-400'
                        }`}>
                          {selectedFile.verdict}
                        </p>
                      </div>
                      <div className="p-4 bg-white/5 rounded-lg">
                        <p className="text-slate-400 text-sm mb-1">Risk Score</p>
                        <p className="text-white font-medium">{selectedFile.risk_score}/100</p>
                      </div>
                      <div className="p-4 bg-white/5 rounded-lg col-span-2">
                        <p className="text-slate-400 text-sm mb-1">Upload Time</p>
                        <p className="text-white font-medium">{formatDate(selectedFile.upload_time)}</p>
                      </div>
                      <div className="p-4 bg-white/5 rounded-lg col-span-2">
                        <p className="text-slate-400 text-sm mb-1">File ID</p>
                        <p className="text-white font-mono text-xs">{selectedFile.id}</p>
                      </div>
                      <div className="p-4 bg-white/5 rounded-lg col-span-2">
                        <p className="text-slate-400 text-sm mb-1">User ID</p>
                        <p className="text-white font-mono text-xs">{selectedFile.user_id}</p>
                      </div>
                    </div>

                    <div className={`p-4 rounded-lg border ${
                      selectedFile.verdict === 'SAFE' ? 'bg-green-500/10 border-green-500/30' :
                      selectedFile.verdict === 'SUSPICIOUS' ? 'bg-yellow-500/10 border-yellow-500/30' :
                      selectedFile.verdict === 'HIGH RISK' ? 'bg-orange-500/10 border-orange-500/30' :
                      'bg-red-500/10 border-red-500/30'
                    }`}>
                      <p className={`text-sm ${
                        selectedFile.verdict === 'SAFE' ? 'text-green-300' :
                        selectedFile.verdict === 'SUSPICIOUS' ? 'text-yellow-300' :
                        selectedFile.verdict === 'HIGH RISK' ? 'text-orange-300' :
                        'text-red-300'
                      }`}>
                        <strong>Analysis Status:</strong> {selectedFile.analyzed ? 'Analyzed' : 'Pending'}
                      </p>
                    </div>
                  </div>
                </div>
              </motion.div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
