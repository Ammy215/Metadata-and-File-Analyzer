import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { X, ShieldAlert, Fingerprint, Activity, Tag } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import { getErrorMessage } from '../lib/getErrorMessage';

const VERDICT_TEXT_COLOR = {
  SAFE: 'text-green-400',
  SUSPICIOUS: 'text-yellow-400',
  'HIGH RISK': 'text-orange-400',
  CRITICAL: 'text-red-400',
};

const SEVERITY_STYLES = {
  LOW: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
  MEDIUM: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  HIGH: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  CRITICAL: 'text-red-400 bg-red-500/10 border-red-500/30',
};

const formatBytes = (bytes) => {
  if (!bytes) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
};

// Real per-file analysis findings (metadata, threat matches, entropy, risk
// breakdown) pulled from GET /api/v1/analyze/{fileId} - the same data the
// upload flow shows right after a scan completes. Raw file bytes are
// deleted from disk right after analysis (see storage lifecycle policy),
// so there is deliberately no download/preview here - only the stored
// analysis results, which are all that still exists.
export default function FileDetailModal({ fileId, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!fileId) return;
    setLoading(true);
    setData(null);
    axios
      .get(`/api/v1/analyze/${fileId}`)
      .then((response) => setData(response.data))
      .catch((error) => toast.error(getErrorMessage(error, 'Failed to load file details')))
      .finally(() => setLoading(false));
  }, [fileId]);

  if (!fileId) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-slate-800 rounded-xl border border-white/20 max-w-2xl w-full max-h-[85vh] overflow-y-auto"
      >
        <div className="p-6">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold text-white mb-2">File Details</h2>
              <p className="text-slate-400">Analysis findings for this file</p>
            </div>
            <button onClick={onClose} className="text-slate-400 hover:text-white">
              <X className="w-5 h-5" />
            </button>
          </div>

          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-white mx-auto"></div>
            </div>
          ) : !data ? (
            <p className="text-slate-400 text-center py-12">Couldn't load details for this file.</p>
          ) : (
            <div className="space-y-6">
              {/* Summary */}
              <div className="p-4 bg-white/5 rounded-lg">
                <p className="text-slate-400 text-sm mb-1">File Name</p>
                <p className="text-white font-medium break-all">{data.original_name}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-white/5 rounded-lg">
                  <p className="text-slate-400 text-sm mb-1">File Type</p>
                  <p className="text-white font-medium">{data.mime_type || 'Unknown'}</p>
                </div>
                <div className="p-4 bg-white/5 rounded-lg">
                  <p className="text-slate-400 text-sm mb-1">Size</p>
                  <p className="text-white font-medium">{formatBytes(data.size_bytes)}</p>
                </div>
                <div className="p-4 bg-white/5 rounded-lg">
                  <p className="text-slate-400 text-sm mb-1">Verdict</p>
                  <p className={`font-medium ${VERDICT_TEXT_COLOR[data.verdict] || 'text-slate-400'}`}>
                    {data.verdict}
                  </p>
                </div>
                <div className="p-4 bg-white/5 rounded-lg">
                  <p className="text-slate-400 text-sm mb-1">Risk Score</p>
                  <p className="text-white font-medium">{data.risk_score}/100</p>
                </div>
              </div>

              {/* Hashes */}
              <div>
                <h3 className="text-white font-semibold flex items-center gap-2 mb-3">
                  <Fingerprint className="w-4 h-4 text-blue-400" /> Hashes
                </h3>
                <div className="space-y-2 text-xs font-mono">
                  <div className="p-3 bg-white/5 rounded-lg flex justify-between gap-4">
                    <span className="text-slate-400 flex-shrink-0">SHA256</span>
                    <span className="text-slate-200 break-all text-right">{data.sha256}</span>
                  </div>
                  <div className="p-3 bg-white/5 rounded-lg flex justify-between gap-4">
                    <span className="text-slate-400 flex-shrink-0">SHA1</span>
                    <span className="text-slate-200 break-all text-right">{data.sha1 || '—'}</span>
                  </div>
                  <div className="p-3 bg-white/5 rounded-lg flex justify-between gap-4">
                    <span className="text-slate-400 flex-shrink-0">MD5</span>
                    <span className="text-slate-200 break-all text-right">{data.md5 || '—'}</span>
                  </div>
                </div>
              </div>

              {/* Entropy */}
              {data.entropy && (
                <div>
                  <h3 className="text-white font-semibold flex items-center gap-2 mb-3">
                    <Activity className="w-4 h-4 text-purple-400" /> Entropy
                  </h3>
                  <div className="p-3 bg-white/5 rounded-lg flex justify-between text-sm">
                    <span className="text-slate-300">{data.entropy.classification}</span>
                    <span className="text-white font-medium">{data.entropy.entropy_score.toFixed(2)} / 8.0</span>
                  </div>
                </div>
              )}

              {/* Threat matches */}
              <div>
                <h3 className="text-white font-semibold flex items-center gap-2 mb-3">
                  <ShieldAlert className="w-4 h-4 text-orange-400" /> Threat Matches
                  {data.threats?.length > 0 && (
                    <span className="text-xs text-slate-400">({data.threats.length})</span>
                  )}
                </h3>
                {data.threats?.length > 0 ? (
                  <div className="space-y-2">
                    {data.threats.map((t, i) => (
                      <div key={i} className={`p-3 rounded-lg border text-sm ${SEVERITY_STYLES[t.severity] || SEVERITY_STYLES.LOW}`}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-semibold">{t.rule_name}</span>
                          <span className="text-xs uppercase">{t.severity}</span>
                        </div>
                        {t.description && <p className="opacity-90">{t.description}</p>}
                        {t.matched_data && (
                          <p className="mt-1 font-mono text-xs opacity-75 break-all">Matched: {t.matched_data}</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-400 text-sm">No threats detected.</p>
                )}
              </div>

              {/* Risk factor breakdown */}
              <div>
                <h3 className="text-white font-semibold flex items-center gap-2 mb-3">
                  <ShieldAlert className="w-4 h-4 text-red-400" /> Risk Factor Breakdown
                </h3>
                {data.risk_factors?.length > 0 ? (
                  <div className="space-y-2">
                    {data.risk_factors.map((r, i) => (
                      <div key={i} className="p-3 bg-white/5 rounded-lg flex items-center justify-between text-sm">
                        <div>
                          <span className="text-slate-200 font-medium">{r.factor_name}</span>
                          {r.details && <p className="text-slate-400 text-xs mt-0.5">{r.details}</p>}
                        </div>
                        <span className="text-white font-medium flex-shrink-0">+{r.contribution}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-400 text-sm">No risk factors contributed to the score.</p>
                )}
              </div>

              {/* Metadata */}
              <div>
                <h3 className="text-white font-semibold flex items-center gap-2 mb-3">
                  <Tag className="w-4 h-4 text-slate-400" /> Metadata
                  {data.metadata?.length > 0 && (
                    <span className="text-xs text-slate-400">({data.metadata.length})</span>
                  )}
                </h3>
                {data.metadata?.length > 0 ? (
                  <div className="divide-y divide-white/10">
                    {data.metadata.map((m, i) => (
                      <div key={i} className="py-2 flex items-center justify-between text-sm gap-4">
                        <span className={`flex-shrink-0 ${m.flagged ? 'text-red-400 font-medium' : 'text-slate-400'}`}>
                          {m.category} / {m.key}
                        </span>
                        <span className="text-slate-200 text-right break-all">{m.value ?? '—'}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-400 text-sm">No metadata extracted.</p>
                )}
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
