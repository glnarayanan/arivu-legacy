import { useState } from "react";
import axios from "axios";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import { BookmarkIcon, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";

const API = "/api";

const SIGNUPS_ENABLED = import.meta.env.VITE_SIGNUPS_ENABLED !== "false";

const AuthPage = ({ onLogin }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    name: "",
  });
  const [forgotPasswordOpen, setForgotPasswordOpen] = useState(false);
  const [forgotPasswordEmail, setForgotPasswordEmail] = useState("");
  const [forgotPasswordLoading, setForgotPasswordLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const effectiveIsLogin = !SIGNUPS_ENABLED || isLogin;
      const endpoint = effectiveIsLogin ? "/auth/login" : "/auth/signup";
      const payload = effectiveIsLogin
        ? { email: formData.email, password: formData.password }
        : formData;

      const response = await axios.post(`${API}${endpoint}`, payload, {
        withCredentials: true,
      });

      onLogin(response.data.user);
      toast.success(
        effectiveIsLogin ? "Welcome back!" : "Account created successfully!",
      );
    } catch (error) {
      const errorMsg = error.response?.data?.detail || "Authentication failed";
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    if (!forgotPasswordEmail) return;

    setForgotPasswordLoading(true);

    try {
      await axios.post(`${API}/auth/forgot-password`, {
        email: forgotPasswordEmail,
      });

      toast.success(
        "If an account exists with this email, you will receive a reset link.",
      );
      setForgotPasswordOpen(false);
      setForgotPasswordEmail("");
    } catch (_u75_error) {
      // Still show success to prevent email enumeration
      toast.success(
        "If an account exists with this email, you will receive a reset link.",
      );
      setForgotPasswordOpen(false);
      setForgotPasswordEmail("");
    } finally {
      setForgotPasswordLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-background">
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-md space-y-8"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1, duration: 0.4 }}
          className="text-center"
        >
          <div className="inline-flex items-center justify-center w-16 h-16 border-2 border-foreground bg-primary text-primary-foreground shadow-brutal mb-4">
            <BookmarkIcon className="w-8 h-8" />
          </div>
          <h1 className="font-display text-5xl tracking-wide uppercase mb-2">
            Arivu
          </h1>
          <p className="text-muted-foreground font-mono text-sm uppercase tracking-wider">
            Your AI-powered second brain for the web
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.4 }}
          className="bg-card border-2 border-foreground p-8 shadow-brutal"
        >
          {SIGNUPS_ENABLED ? (
            <div className="flex gap-2 mb-6">
              <Button
                data-testid="login-tab"
                variant={isLogin ? "default" : "outline"}
                className="flex-1"
                onClick={() => setIsLogin(true)}
              >
                LOG IN
              </Button>
              <Button
                data-testid="signup-tab"
                variant={!isLogin ? "default" : "outline"}
                className="flex-1"
                onClick={() => setIsLogin(false)}
              >
                SIGN UP
              </Button>
            </div>
          ) : (
            <div className="mb-6 border-b-2 border-foreground pb-4">
              <h2 className="font-heading text-xl font-bold text-center mb-2 uppercase tracking-wide">
                Log In
              </h2>
              <p className="font-mono text-xs text-muted-foreground text-center uppercase tracking-wider">
                New account registration is disabled. Only existing users can
                log in.
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {SIGNUPS_ENABLED && !isLogin && (
              <div className="space-y-2">
                <Label
                  htmlFor="name"
                  className="font-mono text-xs uppercase tracking-wider"
                >
                  Name
                </Label>
                <Input
                  id="name"
                  data-testid="name-input"
                  type="text"
                  placeholder="JOHN DOE"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  required={!isLogin}
                  maxLength={100}
                  disabled={loading}
                />
              </div>
            )}

            <div className="space-y-2">
              <Label
                htmlFor="email"
                className="font-mono text-xs uppercase tracking-wider"
              >
                Email
              </Label>
              <Input
                id="email"
                data-testid="email-input"
                type="email"
                placeholder="YOU@EXAMPLE.COM"
                value={formData.email}
                onChange={(e) =>
                  setFormData({ ...formData, email: e.target.value })
                }
                required
                maxLength={254}
                disabled={loading}
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label
                  htmlFor="password"
                  className="font-mono text-xs uppercase tracking-wider"
                >
                  Password
                </Label>
                <button
                  type="button"
                  onClick={() => setForgotPasswordOpen(true)}
                  className="font-mono text-xs text-primary hover:underline uppercase tracking-wider"
                >
                  Forgot?
                </button>
              </div>
              <Input
                id="password"
                data-testid="password-input"
                type="password"
                placeholder="••••••••"
                value={formData.password}
                onChange={(e) =>
                  setFormData({ ...formData, password: e.target.value })
                }
                required
                maxLength={128}
                disabled={loading}
              />
            </div>

            <Button
              data-testid="auth-submit-btn"
              type="submit"
              className="w-full"
              disabled={loading}
            >
              {loading
                ? "PROCESSING..."
                : !SIGNUPS_ENABLED || isLogin
                  ? "LOG IN"
                  : "CREATE ACCOUNT"}
            </Button>
          </form>

          <div className="mt-6 pt-4 border-t-2 border-foreground text-center">
            <p className="font-mono text-xs text-muted-foreground uppercase tracking-wider">
              Keyboard shortcuts: Ctrl+K (Add bookmark) • Ctrl+S (Search)
            </p>
          </div>
        </motion.div>
      </motion.div>

      {/* Forgot Password Dialog */}
      <Dialog open={forgotPasswordOpen} onOpenChange={setForgotPasswordOpen}>
        <DialogContent className="rounded-none border-2 border-foreground shadow-brutal">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase tracking-wide">
              Reset Password
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleForgotPassword} className="space-y-4">
            <p className="font-mono text-sm text-muted-foreground">
              Enter your email address and we'll send you a link to reset your
              password.
            </p>
            <div className="space-y-2">
              <Label
                htmlFor="forgot-email"
                className="font-mono text-xs uppercase tracking-wider"
              >
                Email
              </Label>
              <Input
                id="forgot-email"
                type="email"
                placeholder="YOU@EXAMPLE.COM"
                value={forgotPasswordEmail}
                onChange={(e) => setForgotPasswordEmail(e.target.value)}
                required
                maxLength={254}
                disabled={forgotPasswordLoading}
                className="rounded-none border-2 border-foreground font-mono"
              />
            </div>
            <Button
              type="submit"
              disabled={forgotPasswordLoading}
              className="w-full rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
            >
              {forgotPasswordLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  SENDING...
                </>
              ) : (
                "SEND RESET LINK"
              )}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AuthPage;
