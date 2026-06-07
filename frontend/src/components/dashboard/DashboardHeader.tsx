
import { useLanguage } from '@/contexts/LanguageContext';
import { LanguageSelector } from '@/components/LanguageSelector';
import { useAuth } from '@/contexts/AuthContext';
import {
  LogOut,
  LayoutDashboard,
  Database,
  Landmark,
  ShoppingBasket,
  TrendingUp,
  FileText,
  Bot,
  Rocket,
  BarChart3,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { ThemeToggle } from '@/components/ThemeToggle';
import { useTheme } from 'next-themes';

interface DashboardHeaderProps {
  lastUpdateSeconds: number;
  sensorNodeOnline: boolean;
}

export function DashboardHeader({
  lastUpdateSeconds,
  sensorNodeOnline,
}: DashboardHeaderProps) {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { theme } = useTheme();

  const isDark = theme === 'dark';

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const navItems = [
    {
      path: '/dashboard',
      label: 'Home',
      icon: LayoutDashboard,
    },
    {
      path: '/db',
      label: 'Data',
      icon: Database,
    },
    {
      path: '/profile',
      label: 'Schemes',
      icon: Landmark,
    },
    {
      path: '/mandi',
      label: 'Mandi',
      icon: ShoppingBasket,
    },
    {
      path: '/trends',
      label: 'Trends',
      icon: TrendingUp,
    },
    {
      path: '/reports',
      label: 'Reports',
      icon: FileText,
    },
    {
      path: '/advisor',
      label: 'AI',
      icon: Bot,
    },
    {
      path: '/accelerator',
      label: 'Growth',
      icon: Rocket,
    },
    {
      path: '/overview',
      label: 'Overview',
      icon: BarChart3,
    },
  ];

  return (
    <div
      style={{
        position: 'sticky',
        top: '20px',
        zIndex: 50,
        padding: '0 24px',
        display: 'flex',
        justifyContent: 'center',
      }}
    >
<div
  style={{
    width: '100%',
    maxWidth: '1400px',
    height: '58px',
    borderRadius: '18px',
    overflow: 'hidden',
    backdropFilter: 'blur(24px)',
    WebkitBackdropFilter: 'blur(24px)',
    background: isDark ? 'rgba(15,23,42,0.90)' : 'rgba(255,255,255,0.95)',
    border: isDark
      ? '1.5px solid rgba(255,255,255,0.08)'
      : '1.5px solid rgba(15,23,42,0.10)',
    borderTop: isDark
      ? '2px solid rgba(16,185,129,0.40)'
      : '2px solid rgba(16,185,129,0.30)',
    boxShadow: isDark
      ? '0 8px 28px rgba(0,0,0,0.35), 0 2px 6px rgba(0,0,0,0.20)'
      : '0 8px 24px rgba(15,23,42,0.07), 0 2px 6px rgba(15,23,42,0.04)',
  }}
>
        <div
          style={{
            height: '100%',
            padding: '0 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
          }}
        >
          <Link
            to="/"
            style={{
              display: 'flex',
              alignItems: 'center',
              textDecoration: 'none',
              flexShrink: 0,
            }}
          >
            <img
              src="/logo.png"
              alt="SkyView"
              style={{
                height: '44px',
                width: 'auto',
                objectFit: 'contain',
                display: 'block',
              }}
            />
          </Link>

          <nav
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              flex: 1,
              minWidth: 0,
              overflowX: 'auto',
              scrollbarWidth: 'none',
            }}
          >
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              const Icon = item.icon;

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '8px 11px',
                    borderRadius: '11px',
                    textDecoration: 'none',
                    whiteSpace: 'nowrap',
                    fontSize: '11px',
                    fontWeight: isActive ? 700 : 500,
                    flexShrink: 0,
                    transition: 'all 0.25s ease',
                    color: isActive
                      ? isDark
                        ? '#ffffff'
                        : '#0f172a'
                      : isDark
                      ? 'rgba(255,255,255,0.60)'
                      : 'rgba(15,23,42,0.60)',
                    background: isActive
                      ? isDark
                        ? 'rgba(16,185,129,0.14)'
                        : 'rgba(16,185,129,0.10)'
                      : 'transparent',
                    border: isActive
                      ? '1px solid rgba(16,185,129,0.20)'
                      : '1px solid transparent',
                  }}
                >
                  <Icon size={13} />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              flexShrink: 0,
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 10px',
                borderRadius: '999px',
                background: sensorNodeOnline
                  ? 'rgba(16,185,129,0.08)'
                  : 'rgba(239,68,68,0.08)',
              }}
            >
              <div
                style={{
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  background: sensorNodeOnline
                    ? '#10B981'
                    : '#EF4444',
                }}
              />

              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  color: sensorNodeOnline
                    ? '#10B981'
                    : '#EF4444',
                }}
              >
                {lastUpdateSeconds}s
              </span>
            </div>

            <ThemeToggle />
            <LanguageSelector />

            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '10px',
              }}
              className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
            >
              <LogOut
                style={{
                  width: '15px',
                  height: '15px',
                }}
              />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

