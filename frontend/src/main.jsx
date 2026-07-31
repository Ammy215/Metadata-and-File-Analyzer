import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'sonner';
import { AuthProvider } from './contexts/AuthContext';
import App from './App';
import ErrorBoundary from './components/ErrorBoundary';
import './index.css';
import axios from 'axios';

// Empty string (default) keeps every existing axios.get('/api/v1/...') call
// relative, which is correct for local Docker (nginx proxies same-origin).
// For a split deployment (frontend on Vercel, backend on Render - different
// origins), set VITE_API_URL at build time to the real backend URL; axios
// prefixes every relative call with it automatically, no call sites change.
axios.defaults.baseURL = import.meta.env.VITE_API_URL || '';

// Configure axios to prevent caching
axios.defaults.headers.common['Cache-Control'] = 'no-cache, no-store, must-revalidate';
axios.defaults.headers.common['Pragma'] = 'no-cache';
axios.defaults.headers.common['Expires'] = '0';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <App />
            <Toaster
              position="top-right"
              toastOptions={{
                style: {
                  background: 'rgba(30, 41, 59, 0.95)',
                  color: '#f1f5f9',
                  border: '1px solid rgba(148, 163, 184, 0.2)',
                },
              }}
            />
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
