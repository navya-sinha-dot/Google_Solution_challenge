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
        alignItems: 'center',
        gap: '12px',
        width: '100%',
        maxWidth: '1480px',
        margin: '0 auto',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '1400px',
          height: '64px',        // was 58px
          borderRadius: '18px',
          overflow: 'hidden',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          background: isDark ? 'rgba(10,10,10,0.92)' : 'rgba(255,255,255,0.95)',
          border: isDark
            ? '1.5px solid rgba(255,255,255,0.07)'
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
                height: '52px',        // was 44px
                width: 'auto',
                objectFit: 'contain',
                display: 'block',
                filter: isDark
                  ? 'none'
                  : 'drop-shadow(0 1px 3px rgba(0,0,0,0.18))',  // visibility on light bg
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
                    gap: '6px',              // was 5px
                    padding: '9px 13px',     // was 8px 11px
                    borderRadius: '11px',
                    textDecoration: 'none',
                    whiteSpace: 'nowrap',
                    fontSize: '13px',        // was 11px
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
                  <Icon size={15} />         {/* was 13 */}
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
                  background: sensorNodeOnline ? '#10B981' : '#EF4444',
                }}
              />

              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  color: sensorNodeOnline ? '#10B981' : '#EF4444',
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

      <Link
        to="/db"
        style={{
          width: '48px',
          height: '48px',
          borderRadius: '14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          background: location.pathname === '/db'
            ? isDark ? 'rgba(16,185,129,0.18)' : 'rgba(16,185,129,0.12)'
            : isDark ? 'rgba(10,10,10,0.92)' : 'rgba(255,255,255,0.95)',
          border: location.pathname === '/db'
            ? '2px solid #10B981'
            : isDark ? '1.5px solid rgba(255,255,255,0.07)' : '1.5px solid rgba(15,23,42,0.10)',
          boxShadow: isDark
            ? '0 8px 28px rgba(0,0,0,0.35)'
            : '0 8px 24px rgba(15,23,42,0.07)',
          transition: 'all 0.25s ease',
          flexShrink: 0,
        }}
        title="Database Explorer"
        className="hover:scale-105"
      >
        <Database
          style={{
            width: '18px',
            height: '18px',
            color: location.pathname === '/db'
              ? '#10B981'
              : isDark ? 'rgba(255,255,255,0.70)' : 'rgba(15,23,42,0.70)',
          }}
        />
      </Link>
    </div>
  );
}