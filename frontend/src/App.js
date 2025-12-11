import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import BookmarkDetailPage from './pages/BookmarkDetailPage';
import DuplicatesPage from './pages/DuplicatesPage';
import { Toaster } from './components/ui/sonner';
import './App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      setIsAuthenticated(true);
    }
    setLoading(false);
  }, []);

  const handleLogin = (token, user) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setIsAuthenticated(false);
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
