import { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { getErrorMessage } from '../lib/getErrorMessage';

const AuthContext = createContext(null);

// Co-locating the useAuth hook with AuthProvider (rather than a separate
// file) is a standard, widely-used React Context pattern - it only costs
// Fast Refresh a full remount on edits to this file during dev, not a
// correctness issue, so not worth splitting into two files for.
// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  // sessionStorage, not localStorage: localStorage is shared across every
  // tab of the same browser origin, so logging in as a different user in
  // a second tab silently overwrote the first tab's session token - this
  // was the root cause of the multi-session bug (only one session ever
  // actually worked). sessionStorage is scoped per-tab, giving each tab a
  // genuinely independent login.
  const [token, setToken] = useState(sessionStorage.getItem('token'));

  // Configure axios defaults
  // fetchUserProfile is intentionally omitted from deps: it's a new
  // function reference every render (not memoized), and this effect is
  // meant to fire only when `token` actually changes, not on every render.
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUserProfile();
    } else {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // Session heartbeat - update last_login every 2 minutes for accurate session tracking
  useEffect(() => {
    if (!token || !user) return;

    const sendHeartbeat = async () => {
      try {
        await axios.post('/api/v1/auth/heartbeat');
        console.log('Session heartbeat sent');
      } catch (error) {
        // 401: token expired/invalid. 403: account was deactivated/banned
        // since login (the backend already rejects every request for a
        // banned account immediately - it's the frontend that previously
        // didn't react to that until the token separately expired, leaving
        // a banned user's tab looking "logged in" while everything silently
        // failed). Either way the session is over - log out.
        if (error.response?.status === 401 || error.response?.status === 403) {
          console.error('Session no longer valid:', error.response?.data?.detail || error.response?.data?.error);
          logout();
        }
      }
    };

    // Send heartbeat immediately
    sendHeartbeat();

    // Send heartbeat every 2 minutes (120000ms) to keep session active
    const heartbeatInterval = setInterval(sendHeartbeat, 120000);

    return () => clearInterval(heartbeatInterval);
  }, [token, user]);

  // Retries a couple of times on a network failure or 502/503/504 before
  // giving up - confirmed empirically that there's a real several-second
  // window right after a deploy/restart where nginx serves the frontend
  // fine but the backend isn't ready yet. Without this, a returning user
  // who loads the page during that window gets silently logged out by a
  // transient failure that had nothing to do with their session actually
  // being invalid. A real 401 (expired/bad token) still logs out
  // immediately - no reason to delay that legitimate case.
  const fetchUserProfile = async (attempt = 1) => {
    const maxAttempts = 3;
    try {
      const response = await axios.get('/api/v1/auth/me');
      setUser(response.data);
      setLoading(false);
    } catch (error) {
      const serverNotReady = !error.response || [502, 503, 504].includes(error.response.status);
      if (serverNotReady && attempt < maxAttempts) {
        setTimeout(() => fetchUserProfile(attempt + 1), 2000);
        return;
      }
      console.error('Failed to fetch user profile:', error);
      logout();
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      const response = await axios.post('/api/v1/auth/login', {
        email,
        password,
      });

      const { access_token } = response.data;
      
      sessionStorage.setItem('token', access_token);
      setToken(access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      // Fetch full user profile
      const profileResponse = await axios.get('/api/v1/auth/me');
      setUser(profileResponse.data);
      
      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      return {
        success: false,
        error: getErrorMessage(error, 'Login failed'),
      };
    }
  };

  const register = async (email, password, username, fullName) => {
    try {
      await axios.post('/api/v1/auth/register', {
        email,
        password,
        username,
        full_name: fullName,
      });

      // Don't auto-login - user must login manually after registration
      return { success: true };
    } catch (error) {
      console.error('Registration error:', error);
      return {
        success: false,
        error: getErrorMessage(error, 'Registration failed'),
      };
    }
  };

  const logout = () => {
    sessionStorage.removeItem('token');
    setToken(null);
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
  };

  const isAdmin = () => {
    if (!user?.role) return false;
    const role = String(user.role).toUpperCase().trim();
    return role === 'SUPER ADMIN' || role === 'ADMIN' || role === 'SUPER_ADMIN' || role === 'SUPERADMIN';
  };

  const value = {
    user,
    loading,
    login,
    register,
    logout,
    isAdmin,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
