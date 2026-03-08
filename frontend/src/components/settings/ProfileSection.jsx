import { useState, useEffect, useRef } from 'react';
import axiosInstance from '../../utils/axiosConfig';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { toast } from 'sonner';
import { Camera, X, Loader2, Check } from 'lucide-react';
import { motion } from 'framer-motion';

const ProfileSection = () => {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [formData, setFormData] = useState({ name: '', email: '' });
  const [hasChanges, setHasChanges] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await axiosInstance.get('/user/profile');
      setProfile(response.data);
      setFormData({
        name: response.data.name || '',
        email: response.data.email || ''
      });
    } catch (error) {
      toast.error('Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setHasChanges(
      value !== profile?.[field]
    );
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      const updateData = {};
      if (formData.name !== profile.name) updateData.name = formData.name;
      if (formData.email !== profile.email) updateData.email = formData.email;

      if (Object.keys(updateData).length === 0) {
        toast.info('No changes to save');
        setSaving(false);
        return;
      }

      const response = await axiosInstance.put('/user/profile', updateData);
      setProfile(response.data);
      setHasChanges(false);
      toast.success('Profile updated successfully');
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Failed to update profile';
      toast.error(errorMsg);
    } finally {
      setSaving(false);
    }
  };

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file');
      return;
    }

    // Validate file size (1.5MB)
    if (file.size > 1.5 * 1024 * 1024) {
      toast.error('Image too large (max 1.5MB)');
      return;
    }

    setUploadingAvatar(true);

    try {
      // Convert to base64
      const reader = new FileReader();
      reader.onload = async (event) => {
        try {
          await axiosInstance.post('/user/avatar', {
            avatar_data: event.target.result
          });
          await fetchProfile();
          toast.success('Avatar uploaded successfully');
        } catch (error) {
          const errorMsg = error.response?.data?.detail || 'Failed to upload avatar';
          toast.error(errorMsg);
        } finally {
          setUploadingAvatar(false);
        }
      };
      reader.onerror = () => {
        toast.error('Failed to read image file');
        setUploadingAvatar(false);
      };
      reader.readAsDataURL(file);
    } catch (error) {
      toast.error('Failed to process image');
      setUploadingAvatar(false);
    }

    // Reset input
    e.target.value = '';
  };

  const handleRemoveAvatar = async () => {
    try {
      await axiosInstance.delete('/user/avatar');
      await fetchProfile();
      toast.success('Avatar removed');
    } catch (error) {
      toast.error('Failed to remove avatar');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="font-display text-2xl uppercase tracking-wide mb-2">Profile</h2>
        <p className="font-mono text-xs text-muted-foreground uppercase tracking-wider">
          Manage your personal information
        </p>
      </div>

      {/* Avatar Section */}
      <div className="space-y-4">
        <Label className="font-mono text-xs uppercase tracking-wider">Profile Picture</Label>
        <div className="flex items-center gap-6">
          <div className="relative group">
            <div
              className="w-24 h-24 border-2 border-foreground bg-muted flex items-center justify-center overflow-hidden cursor-pointer"
              onClick={handleAvatarClick}
            >
              {uploadingAvatar ? (
                <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
              ) : profile?.avatar_url ? (
                <img
                  src={profile.avatar_url}
                  alt="Avatar"
                  className="w-full h-full object-cover"
                />
              ) : (
                <span className="font-display text-3xl text-muted-foreground">
                  {profile?.name?.charAt(0)?.toUpperCase() || '?'}
                </span>
              )}
            </div>
            <motion.div
              initial={{ opacity: 0 }}
              whileHover={{ opacity: 1 }}
              className="absolute inset-0 bg-foreground/80 flex items-center justify-center cursor-pointer"
              onClick={handleAvatarClick}
            >
              <Camera className="w-6 h-6 text-background" />
            </motion.div>
          </div>
          <div className="flex flex-col gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleAvatarClick}
              disabled={uploadingAvatar}
              className="rounded-none border-2 border-foreground font-mono uppercase text-xs"
            >
              {uploadingAvatar ? 'Uploading...' : 'Upload Photo'}
            </Button>
            {profile?.avatar_url && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRemoveAvatar}
                className="rounded-none border-2 border-transparent hover:border-destructive hover:text-destructive font-mono uppercase text-xs"
              >
                <X className="w-3 h-3 mr-1" />
                Remove
              </Button>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleAvatarChange}
            className="hidden"
          />
        </div>
        <p className="font-mono text-xs text-muted-foreground">
          JPG, PNG, or GIF. Max 1.5MB.
        </p>
      </div>

      {/* Profile Form */}
      <form onSubmit={handleSaveProfile} className="space-y-6">
        <div className="space-y-2">
          <Label htmlFor="name" className="font-mono text-xs uppercase tracking-wider">
            Display Name
          </Label>
          <Input
            id="name"
            type="text"
            value={formData.name}
            onChange={(e) => handleInputChange('name', e.target.value)}
            placeholder="YOUR NAME"
            className="rounded-none border-2 border-foreground font-mono"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="email" className="font-mono text-xs uppercase tracking-wider">
            Email Address
          </Label>
          <Input
            id="email"
            type="email"
            value={formData.email}
            onChange={(e) => handleInputChange('email', e.target.value)}
            placeholder="YOU@EXAMPLE.COM"
            className="rounded-none border-2 border-foreground font-mono"
          />
        </div>

        <div className="pt-4 border-t-2 border-foreground">
          <Button
            type="submit"
            disabled={saving || !hasChanges}
            className="rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                SAVING...
              </>
            ) : (
              <>
                <Check className="w-4 h-4 mr-2" />
                SAVE CHANGES
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default ProfileSection;
