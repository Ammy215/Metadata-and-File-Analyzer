import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, Mail, Lock, AlertCircle, Loader2, Eye, EyeOff, UserRound } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';

export default function Login() {
  const navigate = useNavigate();
  const { login, guestLogin } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [unverified, setUnverified] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [guestLoading, setGuestLoading] = useState(false);

  const handleGuestLogin = async () => {
    setError('');
    setGuestLoading(true);

    const result = await guestLogin();

    if (result.success) {
      toast.success('Continuing as guest - 3 uploads, 4-hour session.');
      navigate('/dashboard');
    } else {
      setError(result.error);
      toast.error(result.error);
    }

    setGuestLoading(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setUnverified(false);
    setLoading(true);

    const result = await login(formData.email, formData.password);

    if (result.success) {
      toast.success('Login successful!');
      navigate('/dashboard');
    } else {
      setError(result.error);
      setUnverified(Boolean(result.unverified));
      toast.error(result.error);
    }

    setLoading(false);
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError('');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        {/* Logo & Title */}
        <div className="text-center mb-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring' }}
            className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl mb-4 shadow-lg"
          >
            <Shield className="w-8 h-8 text-white" />
          </motion.div>
          <h1 className="text-3xl font-bold text-white mb-2">
            Welcome to FileShield
          </h1>
          <p className="text-slate-300">
            Enterprise File Intelligence Platform
          </p>
        </div>

        {/* Login Card */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/20"
        >
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Error Message */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 flex items-center gap-2"
              >
                <AlertCircle className="w-5 h-5 text-red-400" />
                <div className="text-sm text-red-300">
                  <p>{error}</p>
                  {unverified && (
                    <Link
                      to={`/verify-otp?email=${encodeURIComponent(formData.email)}`}
                      className="underline text-red-200 hover:text-white transition-colors"
                    >
                      Verify your email
                    </Link>
                  )}
                </div>
              </motion.div>
            )}

            {/* Email Input */}
            <div>
              <label className="block text-sm font-medium text-slate-200 mb-2">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  placeholder=""
                />
              </div>
            </div>

            {/* Password Input */}
            <div>
              <label className="block text-sm font-medium text-slate-200 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  className="w-full pl-10 pr-10 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  placeholder=""
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors"
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold py-3 rounded-lg hover:from-blue-600 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-900 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="my-6 flex items-center gap-4">
            <div className="flex-1 h-px bg-white/10"></div>
            <span className="text-sm text-slate-400">OR</span>
            <div className="flex-1 h-px bg-white/10"></div>
          </div>

          {/* Guest Login */}
          <button
            type="button"
            onClick={handleGuestLogin}
            disabled={guestLoading}
            className="w-full bg-white/5 border border-white/10 text-slate-200 font-semibold py-3 rounded-lg hover:bg-white/10 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {guestLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Starting guest session...
              </>
            ) : (
              <>
                <UserRound className="w-5 h-5" />
                Continue as Guest
              </>
            )}
          </button>
          <p className="text-center text-xs text-slate-400 mt-2">
            No account needed - 3 uploads, expires in 4 hours
          </p>

          <div className="my-6 flex items-center gap-4">
            <div className="flex-1 h-px bg-white/10"></div>
            <span className="text-sm text-slate-400">OR</span>
            <div className="flex-1 h-px bg-white/10"></div>
          </div>

          {/* Register Link */}
          <p className="text-center text-slate-300">
            Don&apos;t have an account?{' '}
            <Link
              to="/register"
              className="text-blue-400 hover:text-blue-300 font-semibold transition-colors"
            >
              Create one
            </Link>
          </p>
        </motion.div>

        {/* Footer */}
        <p className="text-center text-slate-400 text-sm mt-6">
          © 2026 FileShield. Enterprise-grade security.
        </p>
      </motion.div>
    </div>
  );
}
