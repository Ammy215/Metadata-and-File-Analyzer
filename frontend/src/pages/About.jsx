import { motion } from 'framer-motion';
import { Shield } from 'lucide-react';

export default function About() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 pt-20 px-4 pb-8">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl mb-4">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-gradient mb-4">About FileShield</h1>
          <p className="text-slate-300 text-lg">
            Enterprise File Intelligence Platform
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/20 space-y-6"
        >
          <div>
            <h2 className="text-2xl font-bold text-white mb-4">What is FileShield?</h2>
            <p className="text-slate-300 leading-relaxed">
              FileShield is an advanced file intelligence and security analysis platform
              that helps you understand the hidden properties, metadata, and potential
              security risks in your files.
            </p>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-white mb-4">Features</h2>
            <ul className="space-y-2 text-slate-300">
              <li className="flex items-start gap-2">
                <span className="text-blue-400">•</span>
                <span>Advanced threat detection and risk scoring</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400">•</span>
                <span>Comprehensive metadata extraction</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400">•</span>
                <span>Entropy analysis for encrypted/compressed files</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400">•</span>
                <span>Keyword and pattern detection</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400">•</span>
                <span>Enterprise-grade security and audit logging</span>
              </li>
            </ul>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-white mb-4">Version</h2>
            <p className="text-slate-300">FileShield v2.0.0 Enterprise</p>
          </div>

          <div className="pt-4 border-t border-white/10">
            <p className="text-slate-400 text-sm text-center">
              © 2026 FileShield. All rights reserved.
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
