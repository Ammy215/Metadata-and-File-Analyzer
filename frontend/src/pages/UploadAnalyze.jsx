import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, Shield, Zap, AlertCircle, CheckCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { AnimatedDropZone } from '../components/FileUpload/AnimatedDropZone';
import axios from 'axios';
import { toast } from 'sonner';
import { getErrorMessage } from '../lib/getErrorMessage';

// GET /api/v1/analyze/{id} returns 202 while analysis is still running
// (the file is processed asynchronously via Celery) - poll until it
// returns a non-202 response instead of the one-shot POST this used to
// call, which hit a route that never existed on the backend.
const pollForAnalysis = async (fileId, { intervalMs = 2000, maxAttempts = 30 } = {}) => {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const response = await axios.get(`/api/v1/analyze/${fileId}`);
    if (response.status !== 202) {
      return response.data;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error('Analysis is taking longer than expected. Please check back shortly.');
};

export default function UploadAnalyze() {
  const { user } = useAuth();
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);

  const handleFileUpload = async (file) => {
    setUploading(true);
    setUploadProgress(0);
    setResult(null);

    try {
      // Step 1: Upload file
      const formData = new FormData();
      formData.append('file', file);

      const uploadResponse = await axios.post('/api/v1/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            setUploadProgress(Math.round((progressEvent.loaded / progressEvent.total) * 100));
          }
        },
      });

      const fileId = uploadResponse.data.file_id;
      toast.success('File uploaded successfully!');

      setUploading(false);
      setAnalyzing(true);

      // Step 2: Poll until analysis completes
      const analysisResult = await pollForAnalysis(fileId);
      setResult(analysisResult);
      toast.success('Analysis complete!');

    } catch (error) {
      console.error('Upload/Analysis error:', error);
      toast.error(getErrorMessage(error, 'Failed to upload or analyze file'));
    } finally {
      setUploading(false);
      setAnalyzing(false);
    }
  };

  const getVerdictColor = (verdict) => {
    switch (verdict) {
      case 'SAFE': return 'text-green-400 bg-green-500/10 border-green-500/30';
      case 'SUSPICIOUS': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
      case 'HIGH RISK': return 'text-orange-400 bg-orange-500/10 border-orange-500/30';
      case 'CRITICAL': return 'text-red-400 bg-red-500/10 border-red-500/30';
      default: return 'text-slate-400 bg-slate-500/10 border-slate-500/30';
    }
  };

  const getVerdictGlow = (verdict) => {
    switch (verdict) {
      case 'CRITICAL': return 'pulse-critical glow-red';
      case 'HIGH RISK': return 'glow-amber';
      default: return '';
    }
  };

  const getVerdictIcon = (verdict) => {
    switch (verdict) {
      case 'SAFE': return <CheckCircle className="w-5 h-5" />;
      case 'SUSPICIOUS':
      case 'HIGH RISK':
      case 'CRITICAL': return <AlertCircle className="w-5 h-5" />;
      default: return <FileText className="w-5 h-5" />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 pt-20 px-4 pb-8">
      <div className="max-w-6xl mx-auto">
        {/* Welcome Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl font-bold mb-4">
            <span className="text-white">Welcome back, </span>
            <span className="text-gradient">{user?.full_name || user?.username || 'Super Administrator'}</span>
            <span className="text-white">!</span>
          </h1>
          <p className="text-slate-300 text-lg">
            Upload files to analyze for security threats and metadata
          </p>
        </motion.div>

        {/* Upload Section */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/20 mb-8"
        >
          {analyzing ? (
            <div className="rounded-xl border-2 border-dashed border-slate-600 p-12 text-center space-y-4">
              <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-400 mx-auto"></div>
              <p className="text-white font-medium">Analyzing file...</p>
            </div>
          ) : (
            <label>
              <input
                type="file"
                className="hidden"
                onChange={(e) => {
                  const files = e.target.files;
                  if (files && files.length > 0) {
                    handleFileUpload(files[0]);
                  }
                  e.target.value = '';
                }}
                accept=".pdf,.docx,.txt,.exe,.zip,.doc,.xlsx,.pptx,.png,.jpg,.jpeg"
              />
              <AnimatedDropZone
                onFileSelect={handleFileUpload}
                isUploading={uploading}
                uploadProgress={uploadProgress}
              />
            </label>
          )}
          <p className="text-slate-500 text-sm text-center mt-4">
            Supports: PDF, DOCX, TXT, EXE, ZIP, and more (up to 2 GB depending on file type)
          </p>
        </motion.div>

        {/* Analysis Result */}
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/20 mb-8"
          >
            <h2 className="text-2xl font-bold text-white mb-6">Analysis Results</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-white/5 rounded-lg">
                  <span className="text-slate-400">Verdict</span>
                  <div className={`flex items-center gap-2 px-3 py-1 rounded-full border ${getVerdictColor(result.verdict)} ${getVerdictGlow(result.verdict)}`}>
                    {getVerdictIcon(result.verdict)}
                    <span className="font-semibold">{result.verdict}</span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between p-4 bg-white/5 rounded-lg">
                  <span className="text-slate-400">Risk Score</span>
                  <span className="text-white font-bold text-xl">{result.risk_score}/100</span>
                </div>
              </div>

              <div className="p-4 bg-white/5 rounded-lg">
                <h3 className="text-sm font-medium text-slate-400 mb-2">Risk Breakdown</h3>
                <div className="space-y-2">
                  {result.risk_factors && result.risk_factors.length > 0 ? (
                    result.risk_factors.map((factor, idx) => (
                      <div key={idx} className="flex justify-between text-sm">
                        <span className="text-slate-300 capitalize">{factor.factor_name?.replace(/_/g, ' ')}</span>
                        <span className="text-white font-medium">+{factor.contribution}</span>
                      </div>
                    ))
                  ) : (
                    <p className="text-slate-500 text-sm">No risk factors detected</p>
                  )}
                </div>
              </div>
            </div>

            {result.threats && result.threats.length > 0 && (
              <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                <h3 className="text-red-400 font-semibold mb-2">⚠️ Threats Detected</h3>
                <ul className="space-y-1">
                  {result.threats.map((threat, idx) => (
                    <li key={idx} className="text-red-300 text-sm">
                      • [{threat.severity}] {threat.rule_name} — {threat.description}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </motion.div>
        )}

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="card-hover bg-white/5 backdrop-blur-lg rounded-xl p-6 border border-white/10"
          >
            <Shield className="w-10 h-10 text-blue-400 mb-4" />
            <h3 className="text-lg font-semibold text-white mb-2">
              Security Analysis
            </h3>
            <p className="text-slate-400 text-sm">
              Advanced threat detection and risk scoring
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="card-hover bg-white/5 backdrop-blur-lg rounded-xl p-6 border border-white/10"
          >
            <FileText className="w-10 h-10 text-purple-400 mb-4" />
            <h3 className="text-lg font-semibold text-white mb-2">
              Metadata Extraction
            </h3>
            <p className="text-slate-400 text-sm">
              Extract hidden metadata and file properties
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="card-hover bg-white/5 backdrop-blur-lg rounded-xl p-6 border border-white/10"
          >
            <Zap className="w-10 h-10 text-yellow-400 mb-4" />
            <h3 className="text-lg font-semibold text-white mb-2">
              Fast Processing
            </h3>
            <p className="text-slate-400 text-sm">
              Get results in seconds with enterprise-grade analysis
            </p>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
