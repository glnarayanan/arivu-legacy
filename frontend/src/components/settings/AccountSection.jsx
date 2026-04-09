import { useState } from 'react';
import axiosInstance from '../../utils/axiosConfig';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { toast } from 'sonner';
import { Loader2, Check as _u7_Check, Eye, EyeOff, ShieldCheck } from 'lucide-react';

const PasswordStrengthIndicator = ({ password }) => {
  const getStrength = () => {
    if (!password) return { level: 0, label: '', color: '' };

    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[a-z]/.test(password)) score++;
    if (/\d/.test(password)) score++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++;

    if (score <= 2) return { level: 1, label: 'WEAK', color: 'bg-destructive' };
    if (score <= 4) return { level: 2, label: 'FAIR', color: 'bg-amber-500' };
    if (score <= 5) return { level: 3, label: 'GOOD', color: 'bg-blue-500' };
    return { level: 4, label: 'STRONG', color: 'bg-green-600' };
  };

  const strength = getStrength();
  if (!password) return null;

  return (
    <div className="mt-2 space-y-1">
      <div className="flex gap-1">
        {[1, 2, 3, 4].map((level) => (
          <div
            key={level}
            className={`h-1 flex-1 ${level <= strength.level ? strength.color : 'bg-muted'}`}
          />
        ))}
      </div>
      <p className={`font-mono text-xs uppercase tracking-wider ${strength.level <= 1 ? 'text-destructive' :
          strength.level <= 2 ? 'text-amber-600' :
            strength.level <= 3 ? 'text-blue-600' : 'text-green-600'
        }`}>
        {strength.label}
      </p>
    </div>
  );
};

const AccountSection = () => {
  const [loading, setLoading] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [formData, setFormData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [errors, setErrors] = useState({});

  const validateForm = () => {
    const newErrors = {};

    if (!formData.currentPassword) {
      newErrors.currentPassword = 'Current password is required';
    }

    if (!formData.newPassword) {
      newErrors.newPassword = 'New password is required';
    } else if (formData.newPassword.length < 8) {
      newErrors.newPassword = 'Password must be at least 8 characters';
    } else if (!/[A-Z]/.test(formData.newPassword)) {
      newErrors.newPassword = 'Password must contain an uppercase letter';
    } else if (!/[a-z]/.test(formData.newPassword)) {
      newErrors.newPassword = 'Password must contain a lowercase letter';
    } else if (!/\d/.test(formData.newPassword)) {
      newErrors.newPassword = 'Password must contain a number';
    } else if (!/[!@#$%^&*(),.?":{}|<>]/.test(formData.newPassword)) {
      newErrors.newPassword = 'Password must contain a special character';
    }

    if (formData.newPassword !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) return;

    setLoading(true);

    try {
      await axiosInstance.post('/auth/change-password', {
        current_password: formData.currentPassword,
        new_password: formData.newPassword
      });

      toast.success('Password changed successfully');
      setFormData({ currentPassword: '', newPassword: '', confirmPassword: '' });
      setErrors({});
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Failed to change password';
      toast.error(errorMsg);
      if (errorMsg.includes('Current password')) {
        setErrors({ currentPassword: errorMsg });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="font-display text-2xl uppercase tracking-wide mb-2">Account Security</h2>
        <p className="font-mono text-xs text-muted-foreground uppercase tracking-wider">
          Change your password
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Current Password */}
        <div className="space-y-2">
          <Label htmlFor="currentPassword" className="font-mono text-xs uppercase tracking-wider">
            Current Password
          </Label>
          <div className="relative">
            <Input
              id="currentPassword"
              type={showCurrentPassword ? 'text' : 'password'}
              value={formData.currentPassword}
              onChange={(e) => setFormData(prev => ({ ...prev, currentPassword: e.target.value }))}
              placeholder="••••••••"
              className={`rounded-none border-2 font-mono pr-10 ${errors.currentPassword ? 'border-destructive' : 'border-foreground'
                }`}
            />
            <button
              type="button"
              onClick={() => setShowCurrentPassword(!showCurrentPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {errors.currentPassword && (
            <p className="font-mono text-xs text-destructive">{errors.currentPassword}</p>
          )}
        </div>

        {/* New Password */}
        <div className="space-y-2">
          <Label htmlFor="newPassword" className="font-mono text-xs uppercase tracking-wider">
            New Password
          </Label>
          <div className="relative">
            <Input
              id="newPassword"
              type={showNewPassword ? 'text' : 'password'}
              value={formData.newPassword}
              onChange={(e) => setFormData(prev => ({ ...prev, newPassword: e.target.value }))}
              placeholder="••••••••"
              className={`rounded-none border-2 font-mono pr-10 ${errors.newPassword ? 'border-destructive' : 'border-foreground'
                }`}
            />
            <button
              type="button"
              onClick={() => setShowNewPassword(!showNewPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <PasswordStrengthIndicator password={formData.newPassword} />
          {errors.newPassword && (
            <p className="font-mono text-xs text-destructive">{errors.newPassword}</p>
          )}
        </div>

        {/* Confirm Password */}
        <div className="space-y-2">
          <Label htmlFor="confirmPassword" className="font-mono text-xs uppercase tracking-wider">
            Confirm New Password
          </Label>
          <div className="relative">
            <Input
              id="confirmPassword"
              type={showConfirmPassword ? 'text' : 'password'}
              value={formData.confirmPassword}
              onChange={(e) => setFormData(prev => ({ ...prev, confirmPassword: e.target.value }))}
              placeholder="••••••••"
              className={`rounded-none border-2 font-mono pr-10 ${errors.confirmPassword ? 'border-destructive' : 'border-foreground'
                }`}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {errors.confirmPassword && (
            <p className="font-mono text-xs text-destructive">{errors.confirmPassword}</p>
          )}
        </div>

        {/* Password Requirements */}
        <div className="p-4 bg-muted border-2 border-foreground">
          <p className="font-mono text-xs uppercase tracking-wider mb-2 font-medium">
            Password Requirements
          </p>
          <ul className="font-mono text-xs text-muted-foreground space-y-1">
            <li>• At least 8 characters long</li>
            <li>• One uppercase letter (A-Z)</li>
            <li>• One lowercase letter (a-z)</li>
            <li>• One number (0-9)</li>
            <li>• One special character (!@#$%^&*)</li>
          </ul>
        </div>

        <div className="pt-4 border-t-2 border-foreground">
          <Button
            type="submit"
            disabled={loading}
            className="rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                UPDATING...
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4 mr-2" />
                CHANGE PASSWORD
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default AccountSection;
