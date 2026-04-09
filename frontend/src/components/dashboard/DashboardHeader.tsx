import { useLanguage } from '@/contexts/LanguageContext';
import { LanguageSelector } from '@/components/LanguageSelector';
import { useAuth } from '@/contexts/AuthContext';
import { Cloud, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { ThemeToggle } from '@/components/ThemeToggle';
import { useTheme } from 'next-themes';

interface DashboardHeaderProps {
  lastUpdateSeconds: number;
  sensorNodeOnline: boolean;
}

export function DashboardHeader({ lastUpdateSeconds, sensorNodeOnline }: DashboardHeaderProps) {
  const { t } = useLanguage();
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
    { path: '/dashboard', label: t('nav_dashboard') },
    { path: '/profile',   label: t('nav_gov_schemes') },
    { path: '/mandi',     label: t('nav_mandi') },
    { path: '/trends',    label: t('nav_trends') },
    { path: '/reports',   label: t('nav_reports') },
    { path: '/advisor',   label: t('nav_advisor') },
    { path: '/accelerator', label: t('nav_accelerator') },
    { path: '/overview',  label: t('nav_overview') },
  ];

  return (
    <div style={{
      position: 'sticky',
      top: '16px',
      zIndex: 50,
      padding: '8px 8px',
      display: 'flex',
      justifyContent: 'center',
      pointerEvents: 'none',
    }}>
      <div style={{
        pointerEvents: 'auto',
        width: 'max-content',
        background: isDark ? 'rgba(20, 25, 20, 0.8)' : 'rgba(255,255,255,0.85)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: isDark ? '1px solid rgba(255,255,255,0.05)' : '1px solid rgba(0,0,0,0.05)',
        boxShadow: isDark ? '0 10px 40px rgba(0,0,0,0.4)' : '0 10px 40px rgba(0,0,0,0.05)',
        borderRadius: '24px',
        transition: 'all 0.4s ease',
      }}>
        <div style={{
          padding: '0 24px', height: '64px',
          display: 'flex', alignItems: 'center',
          gap: '24px',
        }}>
          {/* Logo */}
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '10px', textDecoration: 'none' }}>
            <div style={{
              width: '36px', height: '36px', borderRadius: '10px',
              background: '#2ECC71',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Cloud style={{ color: 'white', width: '20px', height: '20px' }} />
            </div>
            <span style={{
              fontSize: '20px', fontWeight: '800',
              color: isDark ? '#fff' : '#1B3A20',
              letterSpacing: '-0.3px',
            }}>
              SkyView{' '}
              <span style={{ color: '#2ECC71' }}>AI</span>
            </span>
          </Link>

          {/* Central Nav — Desktop */}
          <nav style={{
            display: 'flex', alignItems: 'center', gap: '4px',
            background: 'transparent',
            padding: '0',
          }}>
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  style={{
                    padding: '8px 16px',
                    borderRadius: '12px',
                    fontSize: '13px', fontWeight: 600,
                    textDecoration: 'none',
                    transition: 'all 0.2s ease',
                    color: isActive
                      ? isDark ? '#2ECC71' : '#1B3A20'
                      : isDark ? '#A8D89A' : '#5A7A60',
                    background: isActive
                      ? isDark ? 'rgba(255,255,255,0.05)' : '#fff'
                      : 'transparent',
                    boxShadow: isActive && !isDark ? '0 2px 10px rgba(0,0,0,0.05)' : 'none',
                    border: isActive && !isDark ? '1px solid rgba(0,0,0,0.02)' : '1px solid transparent',
                  }}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* Right Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {/* Sensor Status */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              paddingRight: '14px',
              borderRight: isDark ? '1px solid rgba(255,255,255,0.1)' : '1px solid rgba(0,0,0,0.1)',
            }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                background: sensorNodeOnline ? 'rgba(46,204,113,0.1)' : 'rgba(229,57,53,0.1)',
                padding: '6px 10px',
                borderRadius: '20px',
              }}>
                <div style={{
                  width: '8px', height: '8px', borderRadius: '50%',
                  background: sensorNodeOnline ? '#2ECC71' : '#E53935',
                }} />
                <span style={{
                  fontSize: '11px', fontWeight: 700,
                  color: sensorNodeOnline ? (isDark ? '#2ECC71' : '#1B3A20') : '#E53935',
                }}>
                  {sensorNodeOnline ? t('status_active') : t('status_offline')}
                </span>
              </div>
              <span style={{
                fontSize: '11px', color: isDark ? '#A8D89A' : '#5A7A60',
                fontWeight: 600,
              }}>
                {t('last_sync')} {lastUpdateSeconds}s
              </span>
            </div>

            {/* Theme, Language, Logout */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              background: isDark ? 'rgba(20, 35, 20, 0.4)' : 'rgba(255,255,255,0.3)',
              padding: '4px', borderRadius: '12px',
              transition: 'all 0.4s ease',
            }}>
              <ThemeToggle />
              <LanguageSelector />
              <Button
                variant="ghost"
                size="icon"
                onClick={handleLogout}
                style={{
                  width: '32px', height: '32px', borderRadius: '8px',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
                className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
              >
                <LogOut style={{ width: '16px', height: '16px' }} />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
