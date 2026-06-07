import { useLanguage } from '@/contexts/LanguageContext';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { FarmBackground, GlassSection } from '@/components/FarmTheme';
import { getSystemHealth, getHistoricalData } from '@/lib/weatherData';
import WeatherLoader from '@/components/WeatherLoader';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area, Legend, ReferenceLine,
} from 'recharts';
import { Thermometer, Droplets, CloudRain, RefreshCw, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useTheme } from 'next-themes';

const API_URL = import.meta.env.VITE_API_URL || '';

interface HistoricalDataPoint {
  time: string;
  temperature: number;
  humidity: number;
  rainfall: number;
}

interface TrendInfo {
  direction: 'rising' | 'falling' | 'stable';
  rate: number;
  avg: number;
  min: number;
  max: number;
}

function computeTrend(data: HistoricalDataPoint[], key: keyof Omit<HistoricalDataPoint, 'time'>): TrendInfo {
  if (!data || data.length < 2) {
    return { direction: 'stable', rate: 0, avg: 0, min: 0, max: 0 };
  }
  const values = data.map(d => d[key] as number);
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  const min = Math.min(...values);
  const max = Math.max(...values);
  // Simple linear regression slope
  const n = values.length;
  const sumX = (n * (n - 1)) / 2;
  const sumY = values.reduce((a, b) => a + b, 0);
  const sumXY = values.reduce((acc, v, i) => acc + i * v, 0);
  const sumX2 = (n * (n - 1) * (2 * n - 1)) / 6;
  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const direction: 'rising' | 'falling' | 'stable' =
    slope > 0.05 ? 'rising' : slope < -0.05 ? 'falling' : 'stable';
  return { direction, rate: Math.round(slope * 100) / 100, avg: Math.round(avg * 10) / 10, min: Math.round(min * 10) / 10, max: Math.round(max * 10) / 10 };
}

// Store computed trends to the backend/database
async function storeTrends(tempTrend: TrendInfo, humidTrend: TrendInfo, rainTrend: TrendInfo) {
  try {
    await fetch(`${API_URL}/api/sensors/trends/store`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        station_id: 'WS01',
        trends: [
          { metric: 'temperature', direction: tempTrend.direction, rate: tempTrend.rate, avg: tempTrend.avg, min: tempTrend.min, max: tempTrend.max },
          { metric: 'humidity', direction: humidTrend.direction, rate: humidTrend.rate, avg: humidTrend.avg, min: humidTrend.min, max: humidTrend.max },
          { metric: 'rainfall', direction: rainTrend.direction, rate: rainTrend.rate, avg: rainTrend.avg, min: rainTrend.min, max: rainTrend.max },
        ],
      }),
    });
  } catch {
    // Silent fail — trends storage is best-effort
  }
}

function TrendBadge({ trend, unit }: { trend: TrendInfo; unit: string }) {
  const isDark = document.documentElement.classList.contains('dark');
  const colors = {
    rising: { bg: 'rgba(229,57,53,0.12)', text: '#E53935', icon: <TrendingUp size={14} /> },
    falling: { bg: 'rgba(66,165,245,0.12)', text: '#42A5F5', icon: <TrendingDown size={14} /> },
    stable: { bg: 'rgba(46,204,113,0.12)', text: '#2ECC71', icon: <Minus size={14} /> },
  };
  const c = colors[trend.direction];
  return (
    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '8px' }}>
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: '4px',
        background: c.bg, color: c.text, padding: '4px 10px', borderRadius: '20px',
        fontSize: '12px', fontWeight: 600, fontFamily: "'Nunito', sans-serif",
      }}>
        {c.icon}
        {trend.direction.charAt(0).toUpperCase() + trend.direction.slice(1)} ({trend.rate > 0 ? '+' : ''}{trend.rate}/pt)
      </span>
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: '4px',
        background: isDark ? 'rgba(168,216,154,0.1)' : 'rgba(27,58,32,0.06)',
        color: isDark ? '#A8D89A' : '#1B3A20', padding: '4px 10px', borderRadius: '20px',
        fontSize: '12px', fontWeight: 500, fontFamily: "'Nunito', sans-serif",
      }}>
        Avg: {trend.avg}{unit} &nbsp;|&nbsp; Min: {trend.min}{unit} &nbsp;|&nbsp; Max: {trend.max}{unit}
      </span>
    </div>
  );
}

export default function Trends() {
  const { t } = useLanguage();
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [historicalData, setHistoricalData] = useState<HistoricalDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string>('');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const refreshTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = useCallback(async (showLoading = false) => {
    try {
      if (showLoading) setLoading(true);
      setIsRefreshing(true);
      setError(null);
      const [health, history] = await Promise.all([
        getSystemHealth(),
        getHistoricalData(24),
      ]);
      console.log('📈 Trends data loaded:', { health, historyCount: history.length });
      setSystemHealth(health);
      setHistoricalData(history);
      setLastRefresh(new Date().toLocaleTimeString());

      // Compute trends and store them in the database
      if (history.length >= 2) {
        const tempTrend = computeTrend(history, 'temperature');
        const humidTrend = computeTrend(history, 'humidity');
        const rainTrend = computeTrend(history, 'rainfall');
        storeTrends(tempTrend, humidTrend, rainTrend);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load data';
      console.error('❌ Trends data error:', errorMsg);
      setError(errorMsg);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData(true);

    // Auto-refresh every 15 seconds
    refreshTimerRef.current = setInterval(() => {
      console.log('🔄 Auto-refreshing trends...');
      fetchData(false);
    }, 15000);

    return () => {
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current);
    };
  }, [fetchData]);

  // Compute current trends
  const tempTrend = computeTrend(historicalData, 'temperature');
  const humidTrend = computeTrend(historicalData, 'humidity');
  const rainTrend = computeTrend(historicalData, 'rainfall');

  // Theme-aware chart colors
  const gridColor = isDark ? 'rgba(46,204,113,0.12)' : 'hsl(var(--border))';
  const axisColor = isDark ? '#6A8A6A' : 'hsl(var(--muted-foreground))';
  const tooltipBg = isDark ? 'rgba(15,25,15,0.9)' : 'hsl(var(--card))';
  const tooltipBorder = isDark ? 'rgba(46,204,113,0.2)' : 'hsl(var(--border))';
  const tooltipLabel = isDark ? '#A8D89A' : 'hsl(var(--foreground))';

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', position: 'relative' }}>
        <FarmBackground />
        <div style={{ position: 'relative', zIndex: 10 }}><WeatherLoader /></div>
      </div>
    );
  }

  if (error || !systemHealth) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', position: 'relative' }}>
        <FarmBackground />
        <GlassSection title="" noHeader>
          <div style={{ padding: '40px', textAlign: 'center' }}>
            <p style={{ color: '#D32F2F', marginBottom: '12px', fontWeight: 700 }}>{error || t('error')}</p>
            <p style={{ color: '#5A7A60', fontSize: '13px' }}>Ensure backend is running on {API_URL}</p>
          </div>
        </GlassSection>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', position: 'relative' }}>
      <FarmBackground />
      <div style={{ position: 'relative', zIndex: 50 }}>
        <DashboardHeader lastUpdateSeconds={systemHealth.lastUpdateSeconds} sensorNodeOnline={systemHealth.sensorNodeOnline} />
      </div>

      <main style={{ position: 'relative', zIndex: 10, maxWidth: '1400px', margin: '0 auto', padding: '32px 20px 60px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '28px' }}>
          <div>
            <h2 style={{
              fontSize: '28px', fontWeight: 800, fontFamily: "'Nunito', sans-serif",
              color: isDark ? '#A8D89A' : '#1B3A20', letterSpacing: '-0.5px',
              transition: 'color 0.4s ease',
            }}>{t('trends')}</h2>
            <p style={{
              fontSize: '14px', color: isDark ? '#6A8A6A' : '#5A7A60',
              fontFamily: "'Nunito', sans-serif",
            }}>
              {t('last_24_hours')} — Real-time data from Neon DB
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {lastRefresh && (
              <span style={{
                fontSize: '11px', color: isDark ? '#6A8A6A' : '#8A9A8C',
                fontFamily: "'Nunito', sans-serif",
              }}>
                Updated: {lastRefresh}
              </span>
            )}
            <button
              onClick={() => fetchData(false)}
              disabled={isRefreshing}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '8px 16px', borderRadius: '12px',
                background: isDark ? 'rgba(46,204,113,0.12)' : 'rgba(27,58,32,0.06)',
                border: `1px solid ${isDark ? 'rgba(46,204,113,0.2)' : 'rgba(27,58,32,0.1)'}`,
                color: isDark ? '#A8D89A' : '#1B3A20',
                fontSize: '13px', fontWeight: 600, fontFamily: "'Nunito', sans-serif",
                cursor: isRefreshing ? 'wait' : 'pointer',
                opacity: isRefreshing ? 0.6 : 1,
                transition: 'all 0.3s ease',
              }}
            >
              <RefreshCw size={14} style={{
                animation: isRefreshing ? 'spin 1s linear infinite' : 'none',
              }} />
              Refresh
            </button>
          </div>
        </div>

        {/* Data count badge */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '6px',
          background: isDark ? 'rgba(46,204,113,0.08)' : 'rgba(46,204,113,0.1)',
          border: `1px solid ${isDark ? 'rgba(46,204,113,0.15)' : 'rgba(46,204,113,0.2)'}`,
          padding: '6px 14px', borderRadius: '20px', marginBottom: '20px',
          fontSize: '12px', fontWeight: 600, fontFamily: "'Nunito', sans-serif",
          color: isDark ? '#2ECC71' : '#1B7A30',
        }}>
          <div style={{
            width: '6px', height: '6px', borderRadius: '50%',
            background: '#2ECC71', animation: 'pulse 2s infinite',
          }} />
          {historicalData.length} data points from DB &nbsp;|&nbsp; Auto-refreshing every 15s
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
          {/* Temperature Trend */}
          <GlassSection title={t('temperature_trend')} icon="️">
            <TrendBadge trend={tempTrend} unit="°C" />
            <div style={{ width: '100%', height: '300px', position: 'relative', marginTop: '12px' }}>
              {historicalData && historicalData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={historicalData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                    <XAxis dataKey="time" stroke={axisColor} fontSize={12} tickLine={false} />
                    <YAxis stroke={axisColor} fontSize={12} tickLine={false} axisLine={false} domain={['auto', 'auto']} unit="°C" />
                    <Tooltip
                      contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}`, borderRadius: '12px', fontSize: '12px' }}
                      labelStyle={{ color: tooltipLabel }}
                      formatter={(value: number) => [`${value}°C`, 'Temperature']}
                    />
                    <ReferenceLine y={tempTrend.avg} stroke="rgba(229,57,53,0.3)" strokeDasharray="5 5" label={{ value: `Avg: ${tempTrend.avg}°C`, position: 'right', fill: axisColor, fontSize: 11 }} />
                    <Line type="monotone" dataKey="temperature" stroke="#E53935" strokeWidth={2.5} dot={false} activeDot={{ r: 5, fill: '#E53935' }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: isDark ? '#6A8A6A' : '#8A9A8C' }}>
                  No data available — waiting for sensor readings
                </div>
              )}
            </div>
          </GlassSection>

          {/* Humidity Trend */}
          <GlassSection title={t('humidity_trend')} icon="">
            <TrendBadge trend={humidTrend} unit="%" />
            <div style={{ width: '100%', height: '300px', position: 'relative', marginTop: '12px' }}>
              {historicalData && historicalData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={historicalData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                    <XAxis dataKey="time" stroke={axisColor} fontSize={12} tickLine={false} />
                    <YAxis stroke={axisColor} fontSize={12} tickLine={false} axisLine={false} domain={[0, 100]} unit="%" />
                    <Tooltip
                      contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}`, borderRadius: '12px', fontSize: '12px' }}
                      labelStyle={{ color: tooltipLabel }}
                      formatter={(value: number) => [`${value}%`, 'Humidity']}
                    />
                    <ReferenceLine y={humidTrend.avg} stroke="rgba(66,165,245,0.3)" strokeDasharray="5 5" label={{ value: `Avg: ${humidTrend.avg}%`, position: 'right', fill: axisColor, fontSize: 11 }} />
                    <Area type="monotone" dataKey="humidity" stroke="#42A5F5" fill={isDark ? 'rgba(66,165,245,0.15)' : 'rgba(66,165,245,0.2)'} strokeWidth={2.5} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: isDark ? '#6A8A6A' : '#8A9A8C' }}>
                  No data available — waiting for sensor readings
                </div>
              )}
            </div>
          </GlassSection>

          {/* Rainfall */}
          <GlassSection title={t('rainfall_accumulation')} icon="️">
            <TrendBadge trend={rainTrend} unit="mm" />
            <div style={{ width: '100%', height: '300px', position: 'relative', marginTop: '12px' }}>
              {historicalData && historicalData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={historicalData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                    <XAxis dataKey="time" stroke={axisColor} fontSize={12} tickLine={false} />
                    <YAxis stroke={axisColor} fontSize={12} tickLine={false} axisLine={false} unit="mm" />
                    <Tooltip
                      contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}`, borderRadius: '12px', fontSize: '12px' }}
                      labelStyle={{ color: tooltipLabel }}
                      formatter={(value: number) => [`${value}mm`, 'Rainfall']}
                    />
                    <Area type="stepAfter" dataKey="rainfall" stroke="#2ECC71" fill={isDark ? 'rgba(46,204,113,0.15)' : 'rgba(46,204,113,0.25)'} strokeWidth={2.5} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: isDark ? '#6A8A6A' : '#8A9A8C' }}>
                  No data available — waiting for sensor readings
                </div>
              )}
            </div>
          </GlassSection>
        </div>
      </main>

      {/* Spin animation for refresh button */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
