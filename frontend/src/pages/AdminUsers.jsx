import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Users, Search, Shield, Ban, Trash2, Eye, Mail } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import TopBar from '../components/layout/TopBar';
import { getErrorMessage } from '../lib/getErrorMessage';

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      console.log('Fetching users from: /api/v1/admin/users');
      const response = await axios.get('/api/v1/admin/users');
      console.log('Users response:', response.data);
      
      // Backend returns {users: [...]} format
      const usersData = response.data.users || [];
      setUsers(usersData);
      
      if (usersData.length === 0) {
        console.log('No users found in database');
      }
    } catch (error) {
      console.error('Failed to fetch users:', error);
      console.error('Error response:', error.response?.data);
      console.error('Error status:', error.response?.status);
      
      // More specific error messages
      if (error.response?.status === 401) {
        toast.error('Session expired. Please login again.');
      } else if (error.response?.status === 403) {
        toast.error('Access denied. Admin privileges required.');
      } else {
        toast.error(`Failed to load users: ${getErrorMessage(error, error.message)}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleBanUser = async (userId) => {
    if (!confirm('Are you sure you want to ban this user?')) return;
    
    try {
      await axios.put(`/api/v1/admin/users/${userId}`, {
        is_active: false
      });
      toast.success('User banned successfully');
      fetchUsers();
    } catch (error) {
      toast.error('Failed to ban user');
    }
  };

  const handleUnbanUser = async (userId) => {
    try {
      await axios.put(`/api/v1/admin/users/${userId}`, {
        is_active: true
      });
      toast.success('User unbanned successfully');
      fetchUsers();
    } catch (error) {
      toast.error('Failed to unban user');
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!confirm('Are you sure you want to DELETE this user? This cannot be undone!')) return;
    
    try {
      await axios.delete(`/api/v1/admin/users/${userId}`);
      toast.success('User deleted successfully');
      fetchUsers();
    } catch (error) {
      toast.error('Failed to delete user');
    }
  };

  const filteredUsers = users.filter(user =>
    user.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.username?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.full_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getRoleBadge = (role) => {
    const badges = {
      SUPER_ADMIN: { color: 'bg-red-500/20 text-red-400', icon: '🛡️', label: 'Super Admin' },
      ADMIN: { color: 'bg-blue-500/20 text-blue-400', icon: '👑', label: 'Admin' },
      USER: { color: 'bg-green-500/20 text-green-400', icon: '👤', label: 'User' },
      GUEST: { color: 'bg-amber-500/20 text-amber-400', icon: '⏱️', label: 'Guest' },
    };
    return badges[role] || badges.USER;
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
            <Users className="w-8 h-8 text-blue-400" />
            <h1 className="text-4xl font-bold text-gradient">User Management</h1>
          </div>
          <p className="text-slate-300 text-lg">
            View and manage all users, their activity, and permissions
          </p>
        </motion.div>

        {/* Search Bar */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="mb-6"
        >
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              placeholder="Search users by email, username, or name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-12 pr-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </motion.div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20">
            <p className="text-slate-400 text-sm">Total Users</p>
            <p className="text-3xl font-bold text-white">{users.length}</p>
          </div>
          <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20">
            <p className="text-slate-400 text-sm">Active Users</p>
            <p className="text-3xl font-bold text-green-400">
              {users.filter(u => u.is_active).length}
            </p>
          </div>
          <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20">
            <p className="text-slate-400 text-sm">Banned Users</p>
            <p className="text-3xl font-bold text-red-400">
              {users.filter(u => !u.is_active).length}
            </p>
          </div>
          <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4 border border-white/20">
            <p className="text-slate-400 text-sm">Admins</p>
            <p className="text-3xl font-bold text-blue-400">
              {users.filter(u => u.role === 'ADMIN' || u.role === 'SUPER_ADMIN').length}
            </p>
          </div>
        </div>

        {/* Users Table */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="bg-white/10 backdrop-blur-lg rounded-xl border border-white/20 overflow-hidden"
        >
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto"></div>
              <p className="text-slate-400 mt-4">Loading users...</p>
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="text-center py-12">
              <Users className="w-16 h-16 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400">No users found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-white/5 border-b border-white/10">
                  <tr>
                    <th className="text-left px-6 py-4 text-sm font-semibold text-slate-300">User</th>
                    <th className="text-left px-6 py-4 text-sm font-semibold text-slate-300">Email</th>
                    <th className="text-left px-6 py-4 text-sm font-semibold text-slate-300">Role</th>
                    <th className="text-left px-6 py-4 text-sm font-semibold text-slate-300">Status</th>
                    <th className="text-left px-6 py-4 text-sm font-semibold text-slate-300">Joined</th>
                    <th className="text-left px-6 py-4 text-sm font-semibold text-slate-300">Last Login</th>
                    <th className="text-right px-6 py-4 text-sm font-semibold text-slate-300">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((user, index) => {
                    const badge = getRoleBadge(user.role);
                    return (
                      <motion.tr
                        key={user.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className="border-b border-white/10 hover:bg-white/5 transition-colors"
                      >
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold">
                              {user.full_name?.charAt(0) || user.username?.charAt(0) || '?'}
                            </div>
                            <div>
                              <p className="text-white font-medium">{user.full_name || user.username}</p>
                              <p className="text-slate-400 text-sm">@{user.username}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <Mail className="w-4 h-4 text-slate-400" />
                            <span className="text-slate-300">{user.email}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium ${badge.color}`}>
                            <span>{badge.icon}</span>
                            {badge.label}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          {user.is_active ? (
                            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400">
                              ● Active
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400">
                              ● Banned
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <span className="text-slate-400 text-sm">
                            {new Date(user.created_at).toLocaleDateString()}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className="text-slate-400 text-sm">
                            {user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => setSelectedUser(user)}
                              className="p-2 hover:bg-white/10 rounded-lg transition-colors group"
                              title="View Details"
                            >
                              <Eye className="w-4 h-4 text-slate-400 group-hover:text-blue-400" />
                            </button>
                            
                            {user.role !== 'SUPER_ADMIN' && (
                              <>
                                {user.is_active ? (
                                  <button
                                    onClick={() => handleBanUser(user.id)}
                                    className="p-2 hover:bg-red-500/10 rounded-lg transition-colors group"
                                    title="Ban User"
                                  >
                                    <Ban className="w-4 h-4 text-slate-400 group-hover:text-red-400" />
                                  </button>
                                ) : (
                                  <button
                                    onClick={() => handleUnbanUser(user.id)}
                                    className="p-2 hover:bg-green-500/10 rounded-lg transition-colors group"
                                    title="Unban User"
                                  >
                                    <Shield className="w-4 h-4 text-slate-400 group-hover:text-green-400" />
                                  </button>
                                )}
                                
                                <button
                                  onClick={() => handleDeleteUser(user.id)}
                                  className="p-2 hover:bg-red-500/10 rounded-lg transition-colors group"
                                  title="Delete User"
                                >
                                  <Trash2 className="w-4 h-4 text-slate-400 group-hover:text-red-400" />
                                </button>
                              </>
                            )}
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

        {/* User Detail Modal */}
        {selectedUser && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-slate-800 rounded-xl border border-white/20 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
            >
              <div className="p-6">
                <div className="flex items-start justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-white mb-2">User Details</h2>
                    <p className="text-slate-400">Complete information about this user</p>
                  </div>
                  <button
                    onClick={() => setSelectedUser(null)}
                    className="text-slate-400 hover:text-white"
                  >
                    ✕
                  </button>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center gap-4 p-4 bg-white/5 rounded-lg">
                    <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-2xl font-semibold">
                      {selectedUser.full_name?.charAt(0) || '?'}
                    </div>
                    <div>
                      <h3 className="text-xl font-semibold text-white">{selectedUser.full_name}</h3>
                      <p className="text-slate-400">@{selectedUser.username}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-white/5 rounded-lg">
                      <p className="text-slate-400 text-sm mb-1">Email</p>
                      <p className="text-white font-medium">{selectedUser.email}</p>
                    </div>
                    <div className="p-4 bg-white/5 rounded-lg">
                      <p className="text-slate-400 text-sm mb-1">Role</p>
                      <p className="text-white font-medium">{selectedUser.role}</p>
                    </div>
                    <div className="p-4 bg-white/5 rounded-lg">
                      <p className="text-slate-400 text-sm mb-1">Status</p>
                      <p className={`font-medium ${selectedUser.is_active ? 'text-green-400' : 'text-red-400'}`}>
                        {selectedUser.is_active ? 'Active' : 'Banned'}
                      </p>
                    </div>
                    <div className="p-4 bg-white/5 rounded-lg">
                      <p className="text-slate-400 text-sm mb-1">Verified</p>
                      <p className={`font-medium ${selectedUser.is_verified ? 'text-green-400' : 'text-yellow-400'}`}>
                        {selectedUser.is_verified ? 'Yes' : 'No'}
                      </p>
                    </div>
                    <div className="p-4 bg-white/5 rounded-lg">
                      <p className="text-slate-400 text-sm mb-1">Joined</p>
                      <p className="text-white font-medium">
                        {new Date(selectedUser.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="p-4 bg-white/5 rounded-lg">
                      <p className="text-slate-400 text-sm mb-1">Last Login</p>
                      <p className="text-white font-medium">
                        {selectedUser.last_login ? new Date(selectedUser.last_login).toLocaleString() : 'Never'}
                      </p>
                    </div>
                  </div>

                  <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                    <p className="text-blue-300 text-sm">
                      ⚠️ <strong>Note:</strong> Passwords are encrypted and cannot be viewed for security reasons.
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
