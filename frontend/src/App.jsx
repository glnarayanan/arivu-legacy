import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import BookmarkDetailPage from './pages/BookmarkDetailPage';
import DuplicatesPage from './pages/DuplicatesPage';
import SettingsPage from './pages/SettingsPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import KnowledgeGraphPage from './pages/KnowledgeGraphPage';
import AnalyticsPage from './pages/AnalyticsPage';
import { Toaster } from './components/ui/sonner';
import axiosInstance from './utils/axiosConfig';
import './App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check authentication via API call (cookies are sent automatically)
    const checkAuth = async () => {
      try {
        const response = await axiosInstance.get('/auth/me');
        if (response.data) {
          setIsAuthenticated(true);
        }
      } catch (error) {
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const handleLogin = (user) => {
    // Tokens are set as HTTP-only cookies by backend
    // No need to store them in localStorage
    setIsAuthenticated(true);
  };

  const handleLogout = async () => {
    try {
      // Call logout endpoint to clear cookies and revoke tokens
      await axiosInstance.post('/auth/logout');
      setIsAuthenticated(false);
    } catch (error) {
      // Even if logout fails, clear local state
      setIsAuthenticated(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="App">
      <div className="grain-texture" />
      <BrowserRouter>
        <Routes>
          <Route
            path="/auth"
            element={
              isAuthenticated ? (
                <Navigate to="/dashboard" replace />
              ) : (
                <AuthPage onLogin={handleLogin} />
              )
            }
          />
          <Route
            path="/dashboard"
            element={
              isAuthenticated ? (
                <DashboardPage onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/bookmark/:id"
            element={
              isAuthenticated ? (
                <BookmarkDetailPage onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/duplicates"
            element={
              isAuthenticated ? (
                <DuplicatesPage onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/settings"
            element={
              isAuthenticated ? (
                <SettingsPage onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/imports"
            element={<Navigate to="/settings?section=import" replace />}
          />
          <Route
            path="/reset-password"
            element={<ResetPasswordPage />}
          />
          <Route
            path="/knowledge-graph"
            element={
              isAuthenticated ? (
                <KnowledgeGraphPage onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/analytics"
            element={
              isAuthenticated ? (
                <AnalyticsPage onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/"
            element={
              isAuthenticated ? (
                <Navigate to="/dashboard" replace />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" />
    </div>
  );
}

export default App;
