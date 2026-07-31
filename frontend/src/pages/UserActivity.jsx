import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Users, Clock, UserCheck, UserX, Calendar, ChevronDown, ChevronUp, LogIn, LogOut, RefreshCw } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function UserActivity() {
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [expandedUsers, setExpandedUsers] = useState([]);
  const [lastFetch, setLastFetch] = useState(null);

  useEffect(() => {
    fetchUserActivity();
    
    // Auto-refresh user data every 10 seconds for real-time accuracy
    const dataInterval = setInterval(() => {
      fetchUserActivity();
    }, 10000);
    
    // Update current time every second for live session display
    const timeInterval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    
    return () => {
      clearInterval(dataInterval);
      clearInterval(timeInterval);
    };
  }, []);

  const fetchUserActivity = async () => {
    try {
      // Add cache-busting timestamp to force fresh data
      const timestamp = new Date().getTime();
      
      // Fetch all users with cache-busting
      const usersResponse = await axios.get(`/api/v1/admin/users?limit=100&_t=${timestamp}`);
      
      console.log('[UserActivity] Fetched users:', usersResponse.data.users?.length || 0);
      
      // Fetch audit logs for login/logout history
      const logsResponse = await axios.get(`/api/v1/admin/audit-logs?days=30&limit=500&_t=${timestamp}`);
      const allLogs = logsResponse.data || [];
      
      console.log('[UserActivity] Fetched audit logs:', allLogs.length);
      
      // Filter login and logout events
      const sessionLogs = allLogs.filter(log => 
        log.action === 'LOGIN' || log.action === 'LOGOUT' || log.action === 'REGISTER'
      );
      
      // Group logs by user
      const userSessionMap = {};
      sessionLogs.forEach(log => {
        if (!log.user_id) return;
        if (!userSessionMap[log.user_id]) {
          userSessionMap[log.user_id] = [];
        }
        userSessionMap[log.user_id].push({
          action: log.action,
          timestamp: log.timestamp,
          ip_address: log.ip_address,
          details: log.details
        });
      });
      
      // Attach session history to users
      const usersWithSessions = (usersResponse.data.users || []).map(user => {
        console.log(`[UserActivity] User ${user.email}: last_login=${user.last_login}`);
        return {
          ...user,
          sessionHistory: (userSessionMap[user.id] || []).sort((a, b) => 
            new Date(b.timestamp) - new Date(a.timestamp)
          )
        };
      });
      
      setUsers(usersWithSessions);
      setLastFetch(new Date());
      
      console.log('[UserActivity] Data updated successfully');
    } catch (error) {
      console.error('[UserActivity] Failed to fetch user activity:', error);
      console.error('[UserActivity] Error details:', error.response?.data);
      toast.error('Failed to load user activity');
    } finally {
      setLoading(false);
    }
  };

  const calculateSessionDuration = (user, useCurrentTime = false) => {
    const lastLogin = user.last_login;
    if (!lastLogin) return { duration: 'Never logged in', isActive: false };
    
    const loginTime = new Date(lastLogin);
    const now = useCurrentTime ? currentTime : new Date();
    const diffMs = now - loginTime;
    const diffMins = Math.floor(diffMs / 60000);
    
    // Check if this is the current logged-in user
    const isCurrentUser = Boolean(currentUser && user.email && user.email === currentUser.email);
    
    // Format session start time
    const sessionStart = loginTime.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      second: '2-digit',
      hour12: true 
    });
    
    const sessionDay = loginTime.toLocaleDateString('en-US', { 
      weekday: 'long',
      month: 'short',
      day: 'numeric'
    });
    
    // Current logged-in user is ALWAYS active
    // OR within 10 minutes for other users (heartbeat updates every 2 min + buffer)
    const isActive = isCurrentUser || diffMins < 10;
    
    if (isActive) {
      // Currently active - show session start to now
      const currentTimeStr = now.toLocaleTimeString('en-US', { 
        hour: 'numeric', 
        minute: '2-digit',
        second: '2-digit',
        hour12: true 
      });
      return {
        duration: `${sessionStart} to ${currentTimeStr}`,
        day: sessionDay,
        isActive: true,
        isCurrentUser,
        minutesActive: diffMins
      };
    } else {
      // Past session - show how long ago
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);
      
      let timeAgo;
      if (diffDays > 0) timeAgo = `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
      else if (diffHours > 0) timeAgo = `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
      else timeAgo = `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
      
      return {
        duration: `Last session: ${sessionStart}`,
        day: sessionDay,
        isActive: false,
        isCurrentUser: false,
        timeAgo
      };
    }
  };

  const isOnline = (user) => {
    if (!user.last_login) return false;
    
    // Current user is always online
    if (currentUser && user.email === currentUser.email) return true;
    
    // Parse the last_login timestamp from backend (UTC ISO format)
    const loginTime = new Date(user.last_login);
    const now = new Date();
    const diffMs = now - loginTime;
    const diffMins = diffMs / 60000;
    
    // Debug logging
    console.log(`[Activity Check] User: ${user.email}`);
    console.log(`  - Last login: ${user.last_login}`);
    console.log(`  - Time diff: ${diffMins.toFixed(2)} minutes ago`);
    console.log(`  - Is current user: ${currentUser && user.email === currentUser.email}`);
    console.log(`  - Should be active: ${diffMins < 10}`);
    
    // Active if within 10 minutes (heartbeat updates every 2 minutes, gives buffer)
    return diffMins < 10;
  };

  const activeUsers = users.filter(user => isOnline(user));
  const pastUsers = users.filter(user => !isOnline(user));
  
  const toggleUserExpansion = (userId) => {
    setExpandedUsers(prev => 
      prev.includes(userId) 
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    );
  };
  
  const formatSessionTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
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
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Users className="w-8 h-8 text-blue-400" />
                <h1 className="text-4xl font-bold text-gradient">User Activity</h1>
              </div>
              <p className="text-slate-300 text-lg">
                Track user sessions and activity timeline
              </p>
              {lastFetch && (
                <div>
                  <p className="text-slate-500 text-sm mt-1">
                    Last updated: {lastFetch.toLocaleTimeString()} • Auto-refresh every 10 seconds
                  </p>
                  <p className="text-slate-600 text-xs mt-0.5">
                    Server time check: {new Date().toLocaleTimeString()} • Users loaded: {users.length}
                  </p>
                </div>
              )}
            </div>
            <button
              onClick={() => {
                setLoading(true);
                fetchUserActivity();
              }}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded-lg text-blue-400 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
              <span className="font-medium">Refresh</span>
            </button>
          </div>
        </motion.div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-500/20 rounded-lg">
                <UserCheck className="w-6 h-6 text-green-400" />
              </div>
              <div>
                <p className="text-slate-400 text-sm">Currently Active</p>
                <p className="text-3xl font-bold text-green-400">{activeUsers.length}</p>
                <p className="text-slate-500 text-xs mt-1">
                  {activeUsers.map(u => u.email?.split('@')[0] || 'unknown').join(', ')}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-slate-500/20 rounded-lg">
                <UserX className="w-6 h-6 text-slate-400" />
              </div>
              <div>
                <p className="text-slate-400 text-sm">Offline Users</p>
                <p className="text-3xl font-bold text-slate-400">{pastUsers.length}</p>
              </div>
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-500/20 rounded-lg">
                <Users className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <p className="text-slate-400 text-sm">Total Users</p>
                <p className="text-3xl font-bold text-blue-400">{users.length}</p>
              </div>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto"></div>
            <p className="text-slate-400 mt-4">Loading user activity...</p>
          </div>
        ) : (
          <>
            {/* Active Users */}
            {activeUsers.length > 0 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mb-8"
              >
                <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                  <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
                  Currently Active Users
                </h2>
                <div className="bg-white/10 backdrop-blur-lg rounded-xl border border-white/20 overflow-hidden">
                  <div className="divide-y divide-white/10">
                    {activeUsers.map((user, index) => {
                      const session = calculateSessionDuration(user, true);
                      const isExpanded = expandedUsers.includes(user.id);
                      const sessionCount = user.sessionHistory?.length || 0;
                      
                      return (
                      <motion.div
                        key={user.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className={`overflow-hidden ${session.isCurrentUser ? 'bg-green-500/10 border-l-4 border-green-500' : ''}`}
                      >
                        <div 
                          className="p-6 hover:bg-white/5 transition-colors cursor-pointer"
                          onClick={() => toggleUserExpansion(user.id)}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <div className={`w-12 h-12 rounded-full ${session.isCurrentUser ? 'bg-gradient-to-br from-green-400 to-green-600 ring-4 ring-green-500/30' : 'bg-gradient-to-br from-green-500 to-blue-600'} flex items-center justify-center text-white font-bold text-lg`}>
                                {user.full_name?.charAt(0) || user.email?.charAt(0)?.toUpperCase() || '?'}
                              </div>
                              <div>
                                <div className="flex items-center gap-2">
                                  <p className="text-white font-semibold">{user.full_name || 'Unnamed User'}</p>
                                  {session.isCurrentUser && (
                                    <span className="px-2 py-0.5 bg-green-500 text-white text-xs rounded-full">You</span>
                                  )}
                                </div>
                                <p className="text-slate-400 text-sm">{user.email}</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-4">
                              <div className="text-right">
                                <div className="flex items-center gap-2 text-green-400 mb-1">
                                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                                  <span className="text-sm font-medium">Active Now</span>
                                </div>
                                <div className="flex items-center gap-2 text-white text-sm mb-1">
                                  <Clock className="w-4 h-4" />
                                  <span className="font-medium">{session.duration}</span>
                                </div>
                                <div className="text-slate-400 text-xs">
                                  {session.day} • {sessionCount} sessions
                                </div>
                              </div>
                              {isExpanded ? (
                                <ChevronUp className="w-5 h-5 text-slate-400" />
                              ) : (
                                <ChevronDown className="w-5 h-5 text-slate-400" />
                              )}
                            </div>
                          </div>
                        </div>
                        
                        {/* Session History */}
                        {isExpanded && user.sessionHistory && user.sessionHistory.length > 0 && (
                          <div className="px-6 pb-6 border-t border-white/10">
                            <h4 className="text-slate-300 text-sm font-semibold mt-4 mb-3">Session History (Last 30 days)</h4>
                            <div className="space-y-2 max-h-60 overflow-y-auto">
                              {user.sessionHistory.map((log, idx) => (
                                <div key={idx} className="flex items-center gap-3 p-3 bg-white/5 rounded-lg">
                                  <div className={`p-2 rounded-lg ${
                                    log.action === 'LOGIN' ? 'bg-green-500/20' :
                                    log.action === 'LOGOUT' ? 'bg-slate-500/20' :
                                    'bg-blue-500/20'
                                  }`}>
                                    {log.action === 'LOGIN' && <LogIn className="w-4 h-4 text-green-400" />}
                                    {log.action === 'LOGOUT' && <LogOut className="w-4 h-4 text-slate-400" />}
                                    {log.action === 'REGISTER' && <UserCheck className="w-4 h-4 text-blue-400" />}
                                  </div>
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                      <span className={`text-sm font-medium ${
                                        log.action === 'LOGIN' ? 'text-green-400' :
                                        log.action === 'LOGOUT' ? 'text-slate-400' :
                                        'text-blue-400'
                                      }`}>
                                        {log.action}
                                      </span>
                                      <span className="text-slate-500 text-xs">•</span>
                                      <span className="text-slate-400 text-xs">{formatSessionTime(log.timestamp)}</span>
                                    </div>
                                    {log.ip_address && (
                                      <p className="text-slate-500 text-xs">IP: {log.ip_address}</p>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </motion.div>
                      );
                    })}
                  </div>
                </div>
              </motion.div>
            )}

            {/* Past Users */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
            >
              <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                <Calendar className="w-6 h-6 text-slate-400" />
                Past User Sessions
              </h2>
              <div className="bg-white/10 backdrop-blur-lg rounded-xl border border-white/20 overflow-hidden">
                {pastUsers.length === 0 ? (
                  <div className="text-center py-12">
                    <Users className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                    <p className="text-slate-400">No past user activity</p>
                  </div>
                ) : (
                  <div className="divide-y divide-white/10">
                    {pastUsers.map((user, index) => {
                      const session = calculateSessionDuration(user, false);
                      return (
                      <motion.div
                        key={user.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className="p-6 hover:bg-white/5 transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-slate-600 to-slate-800 flex items-center justify-center text-white font-bold text-lg">
                              {user.full_name?.charAt(0) || user.email.charAt(0).toUpperCase()}
                            </div>
                            <div>
                              <p className="text-white font-semibold">{user.full_name || 'Unnamed User'}</p>
                              <p className="text-slate-400 text-sm">{user.email}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="flex items-center gap-2 text-slate-400 mb-1">
                              <div className="w-2 h-2 bg-slate-600 rounded-full"></div>
                              <span className="text-sm font-medium">Offline</span>
                            </div>
                            <div className="flex items-center gap-2 text-slate-400 text-sm mb-1">
                              <Clock className="w-4 h-4" />
                              <span>{session.duration}</span>
                            </div>
                            <div className="text-slate-500 text-xs mb-1">
                              {session.timeAgo ? `(${session.timeAgo})` : session.day}
                            </div>
                            {user.created_at && (
                              <div className="text-slate-500 text-xs">
                                Joined: {new Date(user.created_at).toLocaleDateString()}
                              </div>
                            )}
                          </div>
                        </div>
                      </motion.div>
                      );
                    })}
                  </div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </div>
    </div>
  );
}
