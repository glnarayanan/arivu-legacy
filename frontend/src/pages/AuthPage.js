import { useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { BookmarkIcon } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// SIGNUPS DISABLED: Set to true to re-enable signups
const SIGNUPS_ENABLED = false;

const AuthPage = ({ onLogin }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Force login mode when signups are disabled
      const effectiveIsLogin = !SIGNUPS_ENABLED || isLogin;
      const endpoint = effectiveIsLogin ? '/auth/login' : '/auth/signup';
      const payload = effectiveIsLogin
        ? { email: formData.email, password: formData.password }
        : formData;

      const response = await axios.post(`${API}${endpoint}`, payload);

      // Store both access and refresh tokens
      onLogin(response.data.access_token, response.data.refresh_token, response.data.user);
      toast.success(effectiveIsLogin ? 'Welcome back!' : 'Account created successfully!');
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Authentication failed';
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-background">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary text-primary-foreground mb-4">
            <BookmarkIcon className="w-8 h-8" />
          </div>
          <h1 className="font-heading text-4xl font-bold tracking-tight mb-2">
            Arivu
          </h1>
          <p className="text-muted-foreground">
            Your AI-powered second brain for the web
          </p>
        </div>

        <div className="bg-card border border-border rounded-2xl p-8 shadow-sm">
          {SIGNUPS_ENABLED ? (
            <div className="flex gap-2 mb-6">
              <Button
                data-testid="login-tab"
                variant={isLogin ? 'default' : 'ghost'}
                className="flex-1 rounded-full"
                onClick={() => setIsLogin(true)}
              >
                Log In
              </Button>
              <Button
                data-testid="signup-tab"
                variant={!isLogin ? 'default' : 'ghost'}
                className="flex-1 rounded-full"
                onClick={() => setIsLogin(false)}
              >
                Sign Up
              </Button>
            </div>
          ) : (
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-center mb-2">Log In</h2>
              <p className="text-sm text-muted-foreground text-center">
                Signups are currently closed. Only existing users can log in.
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {SIGNUPS_ENABLED && !isLogin && (
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  data-testid="name-input"
                  type="text"
                  placeholder="John Doe"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required={!isLogin}
                  className="rounded-xl"
                />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                data-testid="email-input"
                type="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                className="rounded-xl"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                data-testid="password-input"
                type="password"
                placeholder="••••••••"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
                className="rounded-xl"
              />
            </div>

            <Button
              data-testid="auth-submit-btn"
              type="submit"
              className="w-full rounded-full"
              disabled={loading}
            >
              {loading ? 'Processing...' : (!SIGNUPS_ENABLED || isLogin) ? 'Log In' : 'Create Account'}
            </Button>
          </form>

          <div className="mt-4 text-center text-xs text-muted-foreground">
            <p>Keyboard shortcuts: Ctrl+K (Add bookmark) • Ctrl+S (Search)</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthPage;
