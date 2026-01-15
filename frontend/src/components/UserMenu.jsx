import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, Settings, LogOut, User } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import axiosInstance from '../utils/axiosConfig';

const UserMenu = ({ onLogout }) => {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await axiosInstance.get('/auth/me');
        if (response.data?.email) {
          // Extract username from email (before @)
          const emailUsername = response.data.email.split('@')[0];
          setUsername(emailUsername);
        } else if (response.data?.name) {
          setUsername(response.data.name);
        }
      } catch (error) {
        console.error('Failed to fetch user:', error);
      }
    };
    fetchUser();
  }, []);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          data-testid="user-menu-trigger"
          className="flex items-center gap-2 px-3 py-2 border-2 border-transparent hover:border-foreground hover:bg-muted transition-all font-mono text-sm uppercase tracking-wider"
        >
          <div className="flex items-center justify-center w-6 h-6 border-2 border-foreground bg-primary text-primary-foreground">
            <User className="w-3 h-3" />
          </div>
          <span className="max-w-[120px] truncate">{username || 'User'}</span>
          <ChevronDown className="w-4 h-4" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="start"
        className="w-48 rounded-none border-2 border-foreground shadow-brutal bg-card"
      >
        <DropdownMenuItem
          data-testid="settings-menu-item"
          onClick={() => navigate('/settings')}
          className="cursor-pointer rounded-none font-mono text-sm uppercase tracking-wider hover:bg-muted focus:bg-muted"
        >
          <Settings className="w-4 h-4 mr-2" />
          Settings
        </DropdownMenuItem>
        <DropdownMenuSeparator className="bg-foreground h-[1px]" />
        <DropdownMenuItem
          data-testid="logout-menu-item"
          onClick={onLogout}
          className="cursor-pointer rounded-none font-mono text-sm uppercase tracking-wider hover:bg-muted focus:bg-muted text-destructive focus:text-destructive"
        >
          <LogOut className="w-4 h-4 mr-2" />
          Log Out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default UserMenu;
