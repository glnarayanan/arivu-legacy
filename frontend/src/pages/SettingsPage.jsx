import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Settings as SettingsIcon } from "lucide-react";
import ProfileSection from "../components/settings/ProfileSection";
import AccountSection from "../components/settings/AccountSection";
import ConnectionsSection from "../components/settings/ConnectionsSection";
import ApiKeysSection from "../components/settings/ApiKeysSection";
import ImportSection from "../components/settings/ImportSection";
import BackupSection from "../components/settings/BackupSection";
import DuplicatesSection from "../components/settings/DuplicatesSection";
import AppLayout from "../components/AppLayout";
import axiosInstance from "../utils/axiosConfig";

const BASE_SECTIONS = [
  { id: "profile", label: "Profile" },
  { id: "account", label: "Account" },
  { id: "import", label: "Import" },
  { id: "backup", label: "Backup" },
  { id: "duplicates", label: "Duplicates" },
];

const CONNECTIONS_SECTION = { id: "connections", label: "Connections" };
const API_KEYS_SECTION = { id: "api-keys", label: "API Keys" };

const SettingsPage = ({ onLogout }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeSection, setActiveSection] = useState(
    searchParams.get("section") || "profile",
  );
  const [xEnabled, setXEnabled] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    axiosInstance
      .get("/auth/x/enabled")
      .then((res) => setXEnabled(res.data.enabled))
      .catch(() => setXEnabled(false));
    axiosInstance
      .get("/auth/me")
      .then((res) => setIsAdmin(res.data.is_admin || false))
      .catch(() => setIsAdmin(false));
  }, []);

  const sections = (() => {
    let s = [...BASE_SECTIONS];
    if (xEnabled) {
      s.splice(2, 0, CONNECTIONS_SECTION);
    }
    if (isAdmin) {
      s.splice(xEnabled ? 3 : 2, 0, API_KEYS_SECTION);
    }
    return s;
  })();

  useEffect(() => {
    const section = searchParams.get("section");
    if (section && sections.some((s) => s.id === section)) {
      setActiveSection(section);
    }
  }, [searchParams, sections]);

  const handleSectionChange = (sectionId) => {
    setActiveSection(sectionId);
    setSearchParams({ section: sectionId });
  };

  const renderContent = () => {
    switch (activeSection) {
      case "profile":
        return <ProfileSection />;
      case "account":
        return <AccountSection />;
      case "connections":
        return xEnabled ? <ConnectionsSection /> : <ProfileSection />;
      case "api-keys":
        return isAdmin ? <ApiKeysSection /> : <ProfileSection />;
      case "import":
        return <ImportSection />;
      case "backup":
        return <BackupSection />;
      case "duplicates":
        return <DuplicatesSection />;
      default:
        return <ProfileSection />;
    }
  };

  const activeLabel =
    sections.find((s) => s.id === activeSection)?.label || "Profile";

  return (
    <AppLayout
      onLogout={onLogout}
      showSearch={false}
      settingsSection={activeSection}
      onSettingsSectionChange={handleSectionChange}
      settingsSections={sections}
    >
      <div className="px-6 py-6">
        {/* Page Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="flex items-center justify-center w-10 h-10 border-2 border-foreground bg-primary text-primary-foreground">
            <SettingsIcon className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-heading text-xl font-bold uppercase tracking-wide">
              Settings
            </h2>
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Manage your account and preferences
            </p>
          </div>
        </div>

        {/* Content Area - Full width, no separate sidebar */}
        <div className="bg-card border-2 border-foreground p-6 shadow-brutal">
          {/* Section Header */}
          <div className="mb-6 pb-4 border-b-2 border-foreground">
            <h3 className="font-heading font-bold uppercase tracking-wide">
              {activeLabel}
            </h3>
          </div>
          {renderContent()}
        </div>
      </div>
    </AppLayout>
  );
};

export default SettingsPage;
