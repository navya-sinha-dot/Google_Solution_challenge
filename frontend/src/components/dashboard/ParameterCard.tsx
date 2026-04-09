import { ReactNode } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useTheme } from 'next-themes';
import { ParameterStatus } from '@/lib/weatherData';
import { cn } from '@/lib/utils';

interface ParameterCardProps {
  icon: ReactNode;
  labelKey: string;
  value: number | string;
  unit: string;
  status?: ParameterStatus;
  colorClass?: string;
}

export function ParameterCard({
  icon,
  labelKey,
  value,
  unit,
  status = 'normal',
  colorClass = 'text-blue-500', // Default if not provided
}: ParameterCardProps) {
  const { t } = useLanguage();
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <div
      style={{
        background: isDark ? '#1E1E1E' : '#FFFFFF',
        borderRadius: '16px',
        padding: '16px 20px',
        border: isDark ? '1px solid rgba(255,255,255,0.05)' : '1px solid rgba(0,0,0,0.03)',
        boxShadow: isDark ? '0 4px 12px rgba(0,0,0,0.2)' : '0 4px 12px rgba(0,0,0,0.03)',
        transition: 'all 0.3s ease',
      }}
      className="group hover:shadow-md"
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {/* Icon Circle */}
        <div
          style={{
            width: '48px',
            height: '48px',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: isDark ? 'rgba(255,255,255,0.05)' : '#F0F9FF',
          }}
          className={cn(colorClass)}
        >
          <div>
            {icon}
          </div>
        </div>

        {/* Content Wrapper */}
        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          {/* Top row: Label & Badge */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '4px', marginBottom: '6px' }}>
            <span
              style={{
                fontSize: '14px',
                fontWeight: 500,
                color: isDark ? '#9CA3AF' : '#4B5563',
              }}
            >
              {t(labelKey)}
            </span>
            <StatusPill status={status} />
          </div>

          {/* Bottom row: Value & Unit */}
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
            <span
              style={{
                fontSize: '28px',
                fontWeight: 700,
                color: isDark ? '#F9FAFB' : '#111827',
                letterSpacing: '-0.5px',
                lineHeight: 1,
              }}
            >
              {value}
            </span>
            <span
              style={{
                fontSize: '20px',
                fontWeight: 600,
                color: isDark ? '#E5E7EB' : '#111827',
              }}
            >
              {unit}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: ParameterStatus }) {
  const { t } = useLanguage();
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const getStyle = () => {
    switch (status) {
      case 'normal':
        return { bg: isDark ? 'rgba(16, 185, 129, 0.15)' : '#DCFCE7', text: isDark ? '#34D399' : '#166534' };
      case 'elevated':
        return { bg: isDark ? 'rgba(245, 158, 11, 0.15)' : '#FEF3C7', text: isDark ? '#FBBF24' : '#92400E' };
      case 'critical':
        return { bg: isDark ? 'rgba(239, 68, 68, 0.15)' : '#FEE2E2', text: isDark ? '#F87171' : '#991B1B' };
      default:
        return { bg: isDark ? 'rgba(255,255,255,0.1)' : '#F3F4F6', text: isDark ? '#D1D5DB' : '#374151' };
    }
  };

  const style = getStyle();

  return (
    <span
      style={{
        background: style.bg,
        color: style.text,
        padding: '2px 10px',
        borderRadius: '12px',
        fontSize: '11px',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
      }}
    >
      {t(status)}
    </span>
  );
}
