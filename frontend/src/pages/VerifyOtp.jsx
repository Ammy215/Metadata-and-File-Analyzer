import { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import axios from 'axios';
import { Shield, MailCheck, AlertCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { getErrorMessage } from '../lib/getErrorMessage';

export default function VerifyOtp() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState(searchParams.get('email') || '');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await axios.post('/api/v1/auth/verify-otp', { email, code });
      toast.success('Email verified! You can now log in.');
      navigate('/login');
    } catch (err) {
      const message = getErrorMessage(err, 'Verification failed');
      setError(message);
      toast.error(message);
    }

    setLoading(false);
  };

  const handleResend = async () => {
    if (!email) {
      setError('Enter your email above first');
      return;
    }
    setResending(true);
    try {
      await axios.post('/api/v1/auth/resend-otp', { email });
      toast.success('A new code has been sent, if that account needs verification.');
    } catch (err) {
      toast.error(getErrorMessage(err, 'Could not resend code'));
    }
    setResending(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <div className="text-center mb-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring' }}
            className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl mb-4 shadow-lg"
          >
            <Shield className="w-8 h-8 text-white" />
          </motion.div>
          <h1 className="text-3xl font-bold text-white mb-2">Verify your email</h1>
          <p className="text-slate-300">
            Enter the 6-digit code we sent to your email address
          </p>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/20"
        >
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 flex items-center gap-2"
              >
                <AlertCircle className="w-5 h-5 text-red-400" />
                <p className="text-sm text-red-300">{error}</p>
              </motion.div>
            )}

            <div>
              <label className="block text-sm font-medium text-slate-200 mb-2">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-200 mb-2">
                Verification Code
              </label>
              <div className="relative">
                <MailCheck className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                  required
                  className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-slate-400 tracking-[0.5em] text-center focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  placeholder="000000"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || code.length !== 6}
              className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold py-3 rounded-lg hover:from-blue-600 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-900 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Verifying...
                </>
              ) : (
                'Verify Email'
              )}
            </button>
          </form>

          <div className="my-6 flex items-center gap-4">
            <div className="flex-1 h-px bg-white/10"></div>
            <span className="text-sm text-slate-400">OR</span>
            <div className="flex-1 h-px bg-white/10"></div>
          </div>

          <button
            type="button"
            onClick={handleResend}
            disabled={resending}
            className="w-full text-center text-blue-400 hover:text-blue-300 font-semibold transition-colors disabled:opacity-50"
          >
            {resending ? 'Sending...' : "Didn't get a code? Resend"}
          </button>

          <p className="text-center text-slate-300 mt-6">
            <Link to="/login" className="text-blue-400 hover:text-blue-300 font-semibold transition-colors">
              Back to Sign In
            </Link>
          </p>
        </motion.div>

        <p className="text-center text-slate-400 text-sm mt-6">
          © 2026 FileShield. Enterprise-grade security.
        </p>
      </motion.div>
    </div>
  );
}
