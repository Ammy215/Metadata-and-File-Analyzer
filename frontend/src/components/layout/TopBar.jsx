import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, LayoutDashboard, Upload, History, BarChart3, Info, User, LogOut, ChevronDown, ShieldCheck } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useState } from 'react';

const ADMIN_ITEMS = [
  { path: '/dashboard', label: 'Admin Dashboard' },
  { path: '/admin/users', label: 'Users' },
  { path: '/admin/files', label: 'Files' },
  { path: '/admin/audit-logs', label: 'Audit Logs' },
  { path: '/admin/user-activity', label: 'User Activity' },
  { path: '/admin/threat-analysis', label: 'Threat Analysis' },
];

const TopBar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, isAdmin, isGuest } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showAdminMenu, setShowAdminMenu] = useState(false);

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/upload', label: 'Upload', icon: Upload },
    { path: '/history', label: 'History', icon: History },
    { path: '/statistics', label: 'Statistics', icon: BarChart3 },
    { path: '/about', label: 'About', icon: Info },
  ];

  const isActive = (path) => location.pathname === path;
  const isAdminSection = location.pathname.startsWith('/admin');
  
  const handleLogout = () => {
    logout();
    navigate('/login');
  };
  
  return (
    <motion.div
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="sticky top-0 z-50 border-b border-white/10 bg-slate-900/80 backdrop-blur-xl"
    >
      <div className="container mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/dashboard" className="flex items-center space-x-3 group">
            <motion.div
              whileHover={{ rotate: 360, scale: 1.1 }}
              transition={{ duration: 0.6 }}
              className="relative"
            >
              <Shield className="w-8 h-8 text-blue-400" strokeWidth={2} />
            </motion.div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                FileShield
              </h1>
              <p className="text-xs text-slate-400">File Intelligence Analyzer</p>
            </div>
          </Link>
          
          {/* Navigation */}
          <nav className="flex items-center space-x-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);
              
              return (
                <Link key={item.path} to={item.path} className="relative">
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className={`
                      flex items-center space-x-2 px-4 py-2 rounded-lg
                      transition-all duration-200
                      ${active 
                        ? 'bg-blue-500/10 text-blue-400' 
                        : 'text-slate-400 hover:text-white hover:bg-slate-800'
                      }
                    `}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="text-sm font-medium">{item.label}</span>
                  </motion.div>
                  
                  {active && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-400"
                      initial={false}
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                    />
                  )}
                </Link>
              );
            })}

            {isAdmin() && (
              <div className="relative">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setShowAdminMenu(!showAdminMenu)}
                  className={`
                    flex items-center space-x-2 px-4 py-2 rounded-lg
                    transition-all duration-200
                    ${isAdminSection
                      ? 'bg-blue-500/10 text-blue-400'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800'
                    }
                  `}
                >
                  <ShieldCheck className="w-4 h-4" />
                  <span className="text-sm font-medium">Admin</span>
                  <ChevronDown className={`w-3 h-3 transition-transform ${showAdminMenu ? 'rotate-180' : ''}`} />
                </motion.button>

                <AnimatePresence>
                  {showAdminMenu && (
                    <>
                      <div
                        className="fixed inset-0 z-40"
                        onClick={() => setShowAdminMenu(false)}
                      />
                      <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.2 }}
                        className="absolute left-0 mt-2 w-48 bg-slate-800 rounded-lg shadow-2xl border border-white/10 overflow-hidden z-50"
                      >
                        {ADMIN_ITEMS.map((item) => (
                          <Link
                            key={item.path}
                            to={item.path}
                            onClick={() => setShowAdminMenu(false)}
                            className={`block px-4 py-2 text-sm transition-colors ${
                              isActive(item.path)
                                ? 'bg-blue-500/10 text-blue-400'
                                : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                            }`}
                          >
                            {item.label}
                          </Link>
                        ))}
                      </motion.div>
                    </>
                  )}
                </AnimatePresence>
              </div>
            )}
          </nav>

          {/* User Menu */}
          <div className="relative">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center space-x-3 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-all"
            >
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
              <div className="text-left">
                <p className="text-sm font-medium text-white">
                  {user?.full_name || 'User'}
                </p>
                <p className="text-xs text-slate-400">
                  {isAdmin() ? '🛡️ Admin' : isGuest() ? '⏱️ Guest' : '👤 User'}
                </p>
              </div>
              <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${showUserMenu ? 'rotate-180' : ''}`} />
            </motion.button>

            {/* Dropdown Menu */}
            <AnimatePresence>
              {showUserMenu && (
                <>
                  {/* Backdrop */}
                  <div 
                    className="fixed inset-0 z-40" 
                    onClick={() => setShowUserMenu(false)}
                  />
                  
                  {/* Menu */}
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2 }}
                    className="absolute right-0 mt-2 w-64 bg-slate-800 rounded-lg shadow-2xl border border-white/10 overflow-hidden z-50"
                  >
                    {/* User Info */}
                    <div className="px-4 py-3 bg-slate-900 border-b border-white/10">
                      <p className="text-sm font-medium text-white">
                        {user?.full_name || user?.username || 'User'}
                      </p>
                      {isAdmin() && (
                        <span className="inline-block mt-2 px-2 py-1 text-xs font-medium bg-red-500/20 text-red-400 rounded">
                          🛡️ {user?.role?.replace('_', ' ') || 'ADMIN'}
                        </span>
                      )}
                    </div>

                    {/* Logout */}
                    <div className="border-t border-white/10">
                      <button
                        onClick={handleLogout}
                        className="w-full px-4 py-3 text-left text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors flex items-center gap-3"
                      >
                        <LogOut className="w-4 h-4" />
                        Logout
                      </button>
                    </div>
                  </motion.div>
                </>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {isGuest() && (
        <div className="bg-amber-500/10 border-t border-amber-500/20 px-6 py-2">
          <p className="text-center text-xs text-amber-300">
            ⏱️ Guest session &middot; 3 uploads max &middot; expires 4 hours after starting &middot;{' '}
            <Link to="/register" className="underline hover:text-amber-200 transition-colors">
              Register for a free account
            </Link>
          </p>
        </div>
      )}
    </motion.div>
  );
};

export default TopBar;
