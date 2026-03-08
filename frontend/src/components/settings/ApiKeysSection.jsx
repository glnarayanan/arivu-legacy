import { useState, useEffect } from "react";
import axiosInstance from "../../utils/axiosConfig";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { toast } from "sonner";
import {
  Loader2,
  Eye,
  EyeOff,
  Sparkles,
  Mail,
  Check,
  Trash2,
  ExternalLink,
  Info,
} from "lucide-react";
import { StaggerContainer, StaggerItem } from "../motion/PageOrchestrator";

const XLogo = ({ className = "w-4 h-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
  </svg>
);

const StatusBadge = ({ source, configured }) => {
  if (source === "environment") {
    return (
      <span className="inline-flex items-center px-2 py-0.5 border border-blue-300 bg-blue-100 text-blue-700 font-mono text-xs uppercase tracking-wider">
        ENV
      </span>
    );
  }
  if (source === "database" || configured) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 border border-green-300 bg-green-100 text-green-700 font-mono text-xs uppercase tracking-wider">
        Custom
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 border border-amber-300 bg-amber-100 text-amber-700 font-mono text-xs uppercase tracking-wider">
      Not Set
    </span>
  );
};

const MaskedValue = ({ value }) => {
  if (!value) return null;
  return (
    <div className="px-3 py-2 border-2 border-foreground bg-muted font-mono text-sm tracking-wider">
      {value}
    </div>
  );
};

const ApiKeysSection = () => {
  const [loading, setLoading] = useState(true);
  const [keys, setKeys] = useState(null);
  const [saving, setSaving] = useState({});
  const [deleting, setDeleting] = useState({});

  // Input states
  const [geminiKey, setGeminiKey] = useState("");
  const [showGeminiKey, setShowGeminiKey] = useState(false);
  const [xClientId, setXClientId] = useState("");
  const [showXClientId, setShowXClientId] = useState(false);
  const [xClientSecret, setXClientSecret] = useState("");
  const [showXClientSecret, setShowXClientSecret] = useState(false);
  const [xRedirectUri, setXRedirectUri] = useState("");
  const [xEnabled, setXEnabled] = useState(false);
  const [resendKey, setResendKey] = useState("");
  const [showResendKey, setShowResendKey] = useState(false);

  const fetchKeys = async () => {
    try {
      const response = await axiosInstance.get("/admin/api-keys");
      setKeys(response.data);
      setXEnabled(response.data.x_integration_enabled?.value || false);
      setXRedirectUri(response.data.x_redirect_uri?.value || "");
    } catch (error) {
      console.error("Error fetching API keys:", error);
      toast.error("Failed to load API key configuration");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleSave = async (keyName, values) => {
    setSaving((prev) => ({ ...prev, [keyName]: true }));
    try {
      await axiosInstance.put("/admin/api-keys", values);
      toast.success("API key updated successfully");
      // Clear inputs after save
      if (values.gemini_api_key !== undefined) setGeminiKey("");
      if (values.resend_api_key !== undefined) setResendKey("");
      if (values.x_client_id !== undefined) {
        setXClientId("");
        setXClientSecret("");
      }
      await fetchKeys();
    } catch (error) {
      const detail = error.response?.data?.detail || "Failed to save API key";
      toast.error(detail);
    } finally {
      setSaving((prev) => ({ ...prev, [keyName]: false }));
    }
  };

  const handleDelete = async (keyName) => {
    setDeleting((prev) => ({ ...prev, [keyName]: true }));
    try {
      await axiosInstance.delete(`/admin/api-keys/${keyName}`);
      toast.success("API key removed");
      await fetchKeys();
    } catch (error) {
      const detail = error.response?.data?.detail || "Failed to remove API key";
      toast.error(detail);
    } finally {
      setDeleting((prev) => ({ ...prev, [keyName]: false }));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!keys) return null;

  return (
    <StaggerContainer className="space-y-6">
      {/* Header */}
      <StaggerItem>
        <div>
          <h2 className="font-display text-2xl uppercase tracking-wide mb-2">
            API Configuration
          </h2>
          <p className="font-mono text-xs text-muted-foreground uppercase tracking-wider">
            Configure third-party API keys for your Arivu instance
          </p>
        </div>
      </StaggerItem>

      {/* Gemini AI Card */}
      <StaggerItem>
        <div className="border-2 border-foreground bg-card p-6 shadow-brutal-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex items-center justify-center w-10 h-10 border-2 border-foreground bg-foreground text-background">
              <Sparkles className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-heading font-bold uppercase tracking-wide">
                Gemini AI
              </h4>
              <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Powers AI summaries, tags, and knowledge graph
              </p>
            </div>
            <StatusBadge
              source={keys.gemini_api_key?.source}
              configured={keys.gemini_api_key?.configured}
            />
          </div>

          <div className="space-y-4">
            {keys.gemini_api_key?.masked_value && (
              <div className="space-y-1">
                <Label className="font-mono text-xs uppercase tracking-wider">
                  Current Key
                </Label>
                <MaskedValue value={keys.gemini_api_key.masked_value} />
              </div>
            )}

            <div className="space-y-2">
              <Label
                htmlFor="geminiKey"
                className="font-mono text-xs uppercase tracking-wider"
              >
                {keys.gemini_api_key?.configured ? "Update Key" : "Set Key"}
              </Label>
              <div className="relative">
                <Input
                  id="geminiKey"
                  type={showGeminiKey ? "text" : "password"}
                  value={geminiKey}
                  onChange={(e) => setGeminiKey(e.target.value)}
                  placeholder="Enter Gemini API key"
                  className="rounded-none border-2 border-foreground font-mono pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowGeminiKey(!showGeminiKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showGeminiKey ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Button
                onClick={() =>
                  handleSave("gemini", { gemini_api_key: geminiKey })
                }
                disabled={!geminiKey || saving.gemini}
                className="rounded-none border-2 border-foreground bg-primary text-primary-foreground font-mono uppercase text-xs tracking-wider shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-transform"
              >
                {saving.gemini ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Check className="w-4 h-4 mr-2" />
                )}
                Save
              </Button>
              {keys.gemini_api_key?.source === "database" && (
                <Button
                  variant="outline"
                  onClick={() => handleDelete("gemini_api_key")}
                  disabled={deleting.gemini_api_key}
                  className="rounded-none border-2 border-foreground font-mono uppercase text-xs tracking-wider hover:bg-red-50 hover:text-red-700 hover:border-red-500"
                >
                  {deleting.gemini_api_key ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4 mr-2" />
                  )}
                  Remove
                </Button>
              )}
            </div>

            <div className="flex items-center gap-2 text-muted-foreground">
              <Info className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="font-mono text-xs">
                Get your API key from{" "}
                <a
                  href="https://aistudio.google.com/apikey"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent underline underline-offset-2 inline-flex items-center gap-1 hover:text-accent/80"
                >
                  Google AI Studio
                  <ExternalLink className="w-3 h-3" />
                </a>
              </span>
            </div>
          </div>
        </div>
      </StaggerItem>

      {/* X (Twitter) Integration Card */}
      <StaggerItem>
        <div className="border-2 border-foreground bg-card p-6 shadow-brutal-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex items-center justify-center w-10 h-10 border-2 border-foreground bg-foreground text-background">
              <XLogo className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-heading font-bold uppercase tracking-wide">
                X (Twitter) API
              </h4>
              <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Required for X bookmark import
              </p>
            </div>
          </div>

          <div className="space-y-4">
            {/* Enable/Disable Toggle */}
            <div className="flex items-center justify-between p-3 border-2 border-foreground bg-muted">
              <div>
                <Label className="font-mono text-xs uppercase tracking-wider">
                  X Integration
                </Label>
                <p className="font-mono text-xs text-muted-foreground mt-0.5">
                  {xEnabled ? "Enabled" : "Disabled"}
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  const newValue = !xEnabled;
                  setXEnabled(newValue);
                  handleSave("x_toggle", { x_integration_enabled: newValue });
                }}
                className={`relative inline-flex h-6 w-11 items-center border-2 border-foreground transition-colors ${xEnabled ? "bg-primary" : "bg-muted"}`}
              >
                <span
                  className={`inline-block h-4 w-4 border border-foreground bg-background transition-transform ${xEnabled ? "translate-x-5" : "translate-x-0.5"}`}
                />
              </button>
            </div>

            {/* Client ID */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Label
                  htmlFor="xClientId"
                  className="font-mono text-xs uppercase tracking-wider"
                >
                  Client ID
                </Label>
                <StatusBadge
                  source={keys.x_client_id?.source}
                  configured={keys.x_client_id?.configured}
                />
              </div>
              {keys.x_client_id?.masked_value && (
                <MaskedValue value={keys.x_client_id.masked_value} />
              )}
              <div className="relative">
                <Input
                  id="xClientId"
                  type={showXClientId ? "text" : "password"}
                  value={xClientId}
                  onChange={(e) => setXClientId(e.target.value)}
                  placeholder="Enter X Client ID"
                  className="rounded-none border-2 border-foreground font-mono pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowXClientId(!showXClientId)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showXClientId ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Client Secret */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Label
                  htmlFor="xClientSecret"
                  className="font-mono text-xs uppercase tracking-wider"
                >
                  Client Secret
                </Label>
                <StatusBadge
                  source={keys.x_client_secret?.source}
                  configured={keys.x_client_secret?.configured}
                />
              </div>
              {keys.x_client_secret?.masked_value && (
                <MaskedValue value={keys.x_client_secret.masked_value} />
              )}
              <div className="relative">
                <Input
                  id="xClientSecret"
                  type={showXClientSecret ? "text" : "password"}
                  value={xClientSecret}
                  onChange={(e) => setXClientSecret(e.target.value)}
                  placeholder="Enter X Client Secret"
                  className="rounded-none border-2 border-foreground font-mono pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowXClientSecret(!showXClientSecret)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showXClientSecret ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Redirect URI */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Label
                  htmlFor="xRedirectUri"
                  className="font-mono text-xs uppercase tracking-wider"
                >
                  Redirect URI
                </Label>
                <StatusBadge
                  source={keys.x_redirect_uri?.source}
                  configured={keys.x_redirect_uri?.configured !== false}
                />
              </div>
              <Input
                id="xRedirectUri"
                type="text"
                value={xRedirectUri}
                onChange={(e) => setXRedirectUri(e.target.value)}
                placeholder="https://your-domain.com/settings?section=connections"
                className="rounded-none border-2 border-foreground font-mono"
              />
            </div>

            {/* Save All / Remove Buttons */}
            <div className="flex items-center gap-3">
              <Button
                onClick={() => {
                  const values = {};
                  if (xClientId) values.x_client_id = xClientId;
                  if (xClientSecret) values.x_client_secret = xClientSecret;
                  if (xRedirectUri) values.x_redirect_uri = xRedirectUri;
                  if (Object.keys(values).length === 0) {
                    toast.error("Enter at least one field to save");
                    return;
                  }
                  handleSave("x", values);
                }}
                disabled={
                  saving.x || (!xClientId && !xClientSecret && !xRedirectUri)
                }
                className="rounded-none border-2 border-foreground bg-primary text-primary-foreground font-mono uppercase text-xs tracking-wider shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-transform"
              >
                {saving.x ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Check className="w-4 h-4 mr-2" />
                )}
                Save All
              </Button>
              {keys.x_client_id?.source === "database" && (
                <Button
                  variant="outline"
                  onClick={() => handleDelete("x_client_id")}
                  disabled={deleting.x_client_id}
                  className="rounded-none border-2 border-foreground font-mono uppercase text-xs tracking-wider hover:bg-red-50 hover:text-red-700 hover:border-red-500"
                >
                  {deleting.x_client_id ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4 mr-2" />
                  )}
                  Remove
                </Button>
              )}
            </div>

            <div className="flex items-center gap-2 text-muted-foreground">
              <Info className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="font-mono text-xs">
                Create an app at{" "}
                <a
                  href="https://developer.x.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent underline underline-offset-2 inline-flex items-center gap-1 hover:text-accent/80"
                >
                  developer.x.com
                  <ExternalLink className="w-3 h-3" />
                </a>
              </span>
            </div>
          </div>
        </div>
      </StaggerItem>

      {/* Resend Email Card */}
      <StaggerItem>
        <div className="border-2 border-foreground bg-card p-6 shadow-brutal-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex items-center justify-center w-10 h-10 border-2 border-foreground bg-foreground text-background">
              <Mail className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="font-heading font-bold uppercase tracking-wide">
                Resend Email
              </h4>
              <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Required for password reset emails
              </p>
            </div>
            <StatusBadge
              source={keys.resend_api_key?.source}
              configured={keys.resend_api_key?.configured}
            />
          </div>

          <div className="space-y-4">
            {keys.resend_api_key?.masked_value && (
              <div className="space-y-1">
                <Label className="font-mono text-xs uppercase tracking-wider">
                  Current Key
                </Label>
                <MaskedValue value={keys.resend_api_key.masked_value} />
              </div>
            )}

            <div className="space-y-2">
              <Label
                htmlFor="resendKey"
                className="font-mono text-xs uppercase tracking-wider"
              >
                {keys.resend_api_key?.configured ? "Update Key" : "Set Key"}
              </Label>
              <div className="relative">
                <Input
                  id="resendKey"
                  type={showResendKey ? "text" : "password"}
                  value={resendKey}
                  onChange={(e) => setResendKey(e.target.value)}
                  placeholder="Enter Resend API key"
                  className="rounded-none border-2 border-foreground font-mono pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowResendKey(!showResendKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showResendKey ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Button
                onClick={() =>
                  handleSave("resend", { resend_api_key: resendKey })
                }
                disabled={!resendKey || saving.resend}
                className="rounded-none border-2 border-foreground bg-primary text-primary-foreground font-mono uppercase text-xs tracking-wider shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-transform"
              >
                {saving.resend ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Check className="w-4 h-4 mr-2" />
                )}
                Save
              </Button>
              {keys.resend_api_key?.source === "database" && (
                <Button
                  variant="outline"
                  onClick={() => handleDelete("resend_api_key")}
                  disabled={deleting.resend_api_key}
                  className="rounded-none border-2 border-foreground font-mono uppercase text-xs tracking-wider hover:bg-red-50 hover:text-red-700 hover:border-red-500"
                >
                  {deleting.resend_api_key ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4 mr-2" />
                  )}
                  Remove
                </Button>
              )}
            </div>

            <div className="flex items-center gap-2 text-muted-foreground">
              <Info className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="font-mono text-xs">
                Get your API key from{" "}
                <a
                  href="https://resend.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent underline underline-offset-2 inline-flex items-center gap-1 hover:text-accent/80"
                >
                  resend.com
                  <ExternalLink className="w-3 h-3" />
                </a>
              </span>
            </div>
          </div>
        </div>
      </StaggerItem>
    </StaggerContainer>
  );
};

export default ApiKeysSection;
