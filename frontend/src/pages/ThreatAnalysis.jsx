import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Shield, AlertTriangle, CheckCircle, XCircle, FileWarning, Activity } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

export default function ThreatAnalysis() {
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchThreats();
  }, []);

  const fetchThreats = async () => {
    try {
      // /admin/files caps limit at 100 server-side - this used to request
      // 200 and 422 on every single load, leaving the page permanently
      // empty (same bug class as the earlier Statistics.jsx page_size fix).
      const response = await axios.get('/api/v1/admin/files?limit=100');
      setFiles(response.data || []);
    } catch (error) {
      console.error('Failed to fetch threats:', error);
      toast.error('Failed to load threat data');
    } finally {
      setLoading(false);
    }
  };

  const getThreatCategory = (riskScore) => {
    if (riskScore >= 75) return 'critical';
    if (riskScore >= 50) return 'high';
    if (riskScore >= 25) return 'medium';
    return 'low';
  };

  const getThreatStatus = (verdict, analyzed) => {
    if (!analyzed) return 'pending';
    if (verdict === 'SAFE') return 'treated';
    if (verdict === 'SUSPICIOUS') return 'active';
    return 'harmful';
  };

  const getThreatImpact = (riskScore) => {
    if (riskScore >= 75) return {
      level: 'Critical',
      description: 'Immediate action required. File contains highly suspicious patterns and poses significant security risk.',
      color: 'text-red-400',
      bgColor: 'bg-red-500/20',
      borderColor: 'border-red-500/30',
      glowClass: 'pulse-critical glow-red'
    };
    if (riskScore >= 50) return {
      level: 'High',
      description: 'File shows multiple concerning indicators. Should be quarantined and investigated.',
      color: 'text-orange-400',
      bgColor: 'bg-orange-500/20',
      borderColor: 'border-orange-500/30',
      glowClass: 'glow-amber'
    };
    if (riskScore >= 25) return {
      level: 'Medium',
      description: 'File contains some suspicious characteristics. Monitor for unusual behavior.',
      color: 'text-yellow-400',
      bgColor: 'bg-yellow-500/20',
      borderColor: 'border-yellow-500/30',
      glowClass: ''
    };
    return {
      level: 'Low',
      description: 'File appears safe with standard characteristics. No immediate concerns detected.',
      color: 'text-green-400',
      bgColor: 'bg-green-500/20',
      borderColor: 'border-green-500/30',
      glowClass: ''
    };
  };

  const threats = {
    critical: files.filter(f => getThreatCategory(f.risk_score) === 'critical'),
    high: files.filter(f => getThreatCategory(f.risk_score) === 'high'),
    medium: files.filter(f => getThreatCategory(f.risk_score) === 'medium'),
    low: files.filter(f => getThreatCategory(f.risk_score) === 'low'),
    active: files.filter(f => getThreatStatus(f.verdict, f.analyzed) === 'active'),
    harmful: files.filter(f => getThreatStatus(f.verdict, f.analyzed) === 'harmful'),
    treated: files.filter(f => getThreatStatus(f.verdict, f.analyzed) === 'treated'),
    pending: files.filter(f => getThreatStatus(f.verdict, f.analyzed) === 'pending')
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
          <button
            onClick={() => navigate('/dashboard')}
            className="mb-4 text-slate-400 hover:text-white flex items-center gap-2 transition-colors"
          >
            ← Back to Dashboard
          </button>
          <div className="flex items-center gap-3 mb-2">
            <Shield className="w-8 h-8 text-red-400" />
            <h1 className="text-4xl font-bold text-gradient">Threat Analysis</h1>
          </div>
          <p className="text-slate-300 text-lg">
            Comprehensive threat detection and analysis dashboard
          </p>
        </motion.div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-red-500/10 backdrop-blur-lg rounded-xl p-4 border border-red-500/30">
            <div className="flex items-center gap-3 mb-2">
              <XCircle className="w-5 h-5 text-red-400" />
              <p className="text-red-300 font-semibold">Critical Threats</p>
            </div>
            <p className="text-3xl font-bold text-red-400">{threats.critical.length}</p>
          </div>

          <div className="bg-orange-500/10 backdrop-blur-lg rounded-xl p-4 border border-orange-500/30">
            <div className="flex items-center gap-3 mb-2">
              <AlertTriangle className="w-5 h-5 text-orange-400" />
              <p className="text-orange-300 font-semibold">High Risk</p>
            </div>
            <p className="text-3xl font-bold text-orange-400">{threats.high.length}</p>
          </div>

          <div className="bg-yellow-500/10 backdrop-blur-lg rounded-xl p-4 border border-yellow-500/30">
            <div className="flex items-center gap-3 mb-2">
              <FileWarning className="w-5 h-5 text-yellow-400" />
              <p className="text-yellow-300 font-semibold">Medium Risk</p>
            </div>
            <p className="text-3xl font-bold text-yellow-400">{threats.medium.length}</p>
          </div>

          <div className="bg-green-500/10 backdrop-blur-lg rounded-xl p-4 border border-green-500/30">
            <div className="flex items-center gap-3 mb-2">
              <CheckCircle className="w-5 h-5 text-green-400" />
              <p className="text-green-300 font-semibold">Safe Files</p>
            </div>
            <p className="text-3xl font-bold text-green-400">{threats.low.length}</p>
          </div>
        </div>

        {/* Status Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white/5 backdrop-blur-lg rounded-xl p-4 border border-white/10">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-4 h-4 text-purple-400" />
              <p className="text-slate-300 text-sm">Active Threats</p>
            </div>
            <p className="text-2xl font-bold text-purple-400">{threats.active.length}</p>
          </div>

          <div className="bg-white/5 backdrop-blur-lg rounded-xl p-4 border border-white/10">
            <div className="flex items-center gap-2 mb-2">
              <XCircle className="w-4 h-4 text-red-400" />
              <p className="text-slate-300 text-sm">Harmful</p>
            </div>
            <p className="text-2xl font-bold text-red-400">{threats.harmful.length}</p>
          </div>

          <div className="bg-white/5 backdrop-blur-lg rounded-xl p-4 border border-white/10">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="w-4 h-4 text-green-400" />
              <p className="text-slate-300 text-sm">Treated/Cleared</p>
            </div>
            <p className="text-2xl font-bold text-green-400">{threats.treated.length}</p>
          </div>

          <div className="bg-white/5 backdrop-blur-lg rounded-xl p-4 border border-white/10">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-4 h-4 text-slate-400" />
              <p className="text-slate-300 text-sm">Pending Analysis</p>
            </div>
            <p className="text-2xl font-bold text-slate-400">{threats.pending.length}</p>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto"></div>
            <p className="text-slate-400 mt-4">Loading threat data...</p>
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="space-y-6"
          >
            {files.length === 0 ? (
              <div className="bg-white/10 backdrop-blur-lg rounded-xl border border-white/20 p-12 text-center">
                <Shield className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <p className="text-slate-400">No threat data available</p>
              </div>
            ) : (
              files.map((file, index) => {
                const impact = getThreatImpact(file.risk_score || 0);
                const status = getThreatStatus(file.verdict, file.analyzed);
                
                return (
                  <motion.div
                    key={file.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className={`bg-white/5 backdrop-blur-lg rounded-xl border ${impact.borderColor} overflow-hidden hover:bg-white/10 transition-colors`}
                  >
                    <div className="p-6">
                      {/* Header */}
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center gap-4 flex-1">
                          <div className={`p-3 ${impact.bgColor} rounded-lg`}>
                            {impact.level === 'Critical' && <XCircle className="w-6 h-6 text-red-400" />}
                            {impact.level === 'High' && <AlertTriangle className="w-6 h-6 text-orange-400" />}
                            {impact.level === 'Medium' && <FileWarning className="w-6 h-6 text-yellow-400" />}
                            {impact.level === 'Low' && <CheckCircle className="w-6 h-6 text-green-400" />}
                          </div>
                          <div className="flex-1">
                            <h3 className="text-white font-bold text-lg mb-1">{file.original_name}</h3>
                            <p className="text-slate-400 text-sm">{file.mime_type} • {Math.round(file.size_bytes / 1024)} KB</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${impact.bgColor} ${impact.color} border ${impact.borderColor} ${impact.glowClass}`}>
                            {impact.level} Risk
                          </span>
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                            status === 'active' ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30' :
                            status === 'harmful' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                            status === 'treated' ? 'bg-green-500/20 text-green-400 border border-green-500/30' :
                            'bg-slate-500/20 text-slate-400 border border-slate-500/30'
                          }`}>
                            {status.charAt(0).toUpperCase() + status.slice(1)}
                          </span>
                        </div>
                      </div>

                      {/* Risk Score Bar */}
                      <div className="mb-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-slate-400 text-sm">Risk Score</span>
                          <span className={`text-sm font-bold ${impact.color}`}>{file.risk_score || 0}/100</span>
                        </div>
                        <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all ${
                              file.risk_score >= 75 ? 'bg-red-500' :
                              file.risk_score >= 50 ? 'bg-orange-500' :
                              file.risk_score >= 25 ? 'bg-yellow-500' :
                              'bg-green-500'
                            }`}
                            style={{ width: `${file.risk_score || 0}%` }}
                          />
                        </div>
                      </div>

                      {/* Impact Description */}
                      <div className={`p-4 ${impact.bgColor} rounded-lg border ${impact.borderColor}`}>
                        <p className={`text-sm font-semibold mb-1 ${impact.color}`}>Impact Assessment</p>
                        <p className="text-slate-300 text-sm">{impact.description}</p>
                      </div>

                      {/* Metadata */}
                      <div className="mt-4 pt-4 border-t border-white/10 grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-slate-500">Verdict:</span>
                          <span className="text-white ml-2 font-medium">{file.verdict || 'Pending'}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">Analyzed:</span>
                          <span className="text-white ml-2">{file.analyzed ? 'Yes' : 'No'}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">Upload Time:</span>
                          <span className="text-white ml-2">{new Date(file.upload_time).toLocaleString()}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">File ID:</span>
                          <span className="text-white ml-2 font-mono text-xs">{file.id.slice(0, 8)}...</span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                );
              })
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}
