import { useLanguage } from '@/contexts/LanguageContext';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { FarmBackground, GlassSection } from '@/components/FarmTheme';
import { getSystemHealth, getHistoricalData } from '@/lib/weatherData';
import WeatherLoader from '@/components/WeatherLoader';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area,
} from 'recharts';
import { Thermometer, Droplets, CloudRain } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useTheme } from 'next-themes';

const API_URL = import.meta.env.VITE_API_URL || import.meta.env.REACT_APP_API_URL || 'http://localhost:8000';

interface HistoricalDataPoint {
  time: string;
  temperature: number;
  humidity: number;
  rainfall: number;
}

export default function Trends() {
  const { t } = useLanguage();
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [historicalData, setHistoricalData] = useState<HistoricalDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [health, history] = await Promise.all([
          getSystemHealth(),
          getHistoricalData(24),
        ]);
        console.log(' Trends data loaded:', { health, historyCount: history.length });
        setSystemHealth(health);
        setHistoricalData(history);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to load data';
        console.error(' Trends data error:', errorMsg);
        setError(errorMsg);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

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
        <div style={{ marginBottom: '28px' }}>
          <h2 style={{
            fontSize: '28px', fontWeight: 800, fontFamily: "'Nunito', sans-serif",
            color: isDark ? '#A8D89A' : '#1B3A20', letterSpacing: '-0.5px',
            transition: 'color 0.4s ease',
          }}>{t('trends')}</h2>
          <p style={{
            fontSize: '14px', color: isDark ? '#6A8A6A' : '#5A7A60',
            fontFamily: "'Nunito', sans-serif",
          }}>{t('last_24_hours')}</p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
          {/* Temperature Trend */}
          <GlassSection title={t('temperature_trend')} icon="️">
            <div style={{ width: '100%', height: '300px', position: 'relative' }}>
              {historicalData && historicalData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={historicalData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                    <XAxis dataKey="time" stroke={axisColor} fontSize={12} tickLine={false} />
                    <YAxis stroke={axisColor} fontSize={12} tickLine={false} axisLine={false} domain={['auto', 'auto']} unit="°C" />
                    <Tooltip
                      contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}`, borderRadius: '12px', fontSize: '12px' }}
                      labelStyle={{ color: tooltipLabel }}
                    />
                    <Line type="monotone" dataKey="temperature" stroke="#E53935" strokeWidth={2.5} dot={false} activeDot={{ r: 5, fill: '#E53935' }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: isDark ? '#6A8A6A' : '#8A9A8C' }}>
                  No data available
                </div>
              )}
            </div>
          </GlassSection>

          {/* Humidity Trend */}
          <GlassSection title={t('humidity_trend')} icon="">
            <div style={{ width: '100%', height: '300px', position: 'relative' }}>
              {historicalData && historicalData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={historicalData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                    <XAxis dataKey="time" stroke={axisColor} fontSize={12} tickLine={false} />
                    <YAxis stroke={axisColor} fontSize={12} tickLine={false} axisLine={false} domain={[0, 100]} unit="%" />
                    <Tooltip
                      contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}`, borderRadius: '12px', fontSize: '12px' }}
                      labelStyle={{ color: tooltipLabel }}
                    />
                    <Area type="monotone" dataKey="humidity" stroke="#42A5F5" fill={isDark ? 'rgba(66,165,245,0.15)' : 'rgba(66,165,245,0.2)'} strokeWidth={2.5} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: isDark ? '#6A8A6A' : '#8A9A8C' }}>
                  No data available
                </div>
              )}
            </div>
          </GlassSection>

          {/* Rainfall */}
          <GlassSection title={t('rainfall_accumulation')} icon="️">
            <div style={{ width: '100%', height: '300px', position: 'relative' }}>
              {historicalData && historicalData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={historicalData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                    <XAxis dataKey="time" stroke={axisColor} fontSize={12} tickLine={false} />
                    <YAxis stroke={axisColor} fontSize={12} tickLine={false} axisLine={false} unit="mm" />
                    <Tooltip
                      contentStyle={{ backgroundColor: tooltipBg, border: `1px solid ${tooltipBorder}`, borderRadius: '12px', fontSize: '12px' }}
                      labelStyle={{ color: tooltipLabel }}
                    />
                    <Area type="stepAfter" dataKey="rainfall" stroke="#2ECC71" fill={isDark ? 'rgba(46,204,113,0.15)' : 'rgba(46,204,113,0.25)'} strokeWidth={2.5} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: isDark ? '#6A8A6A' : '#8A9A8C' }}>
                  No data available
                </div>
              )}
            </div>
          </GlassSection>
        </div>
      </main>
    </div>
  );
}
