import { useLanguage } from '@/contexts/LanguageContext';
import { ParameterCard } from '@/components/dashboard/ParameterCard';
import { SystemHealthPanel } from '@/components/dashboard/SystemHealthPanel';
import { StationMapPanel } from '@/components/dashboard/StationMapPanel';
import { AlertsPanel } from '@/components/dashboard/AlertsPanel';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { WeatherInsightPanel } from '@/components/dashboard/WeatherInsightPanel';
import { FarmBackground, GlassSection } from '@/components/FarmTheme';
import WeatherLoader from '@/components/WeatherLoader';
import {
  getCurrentWeatherData,
  getSystemHealth,
  getRecentAlerts,
  getParameterStatus,
  WeatherData,
  SystemHealth,
  Alert,
} from '@/lib/weatherData';
import {
  Thermometer,
  Droplets,
  Gauge,
  Wind,
  Compass,
  CloudRain,
  Sun,
  Lightbulb,
  Cloud,
  ThermometerSun,
  Waves,
} from 'lucide-react';
import { useState, useEffect } from 'react';

// Add pulse animation styles
const styleSheet = document.createElement("style");
styleSheet.textContent = `
  @keyframes pulse {
    0%, 100% {
      opacity: 1;
    }
    50% {
      opacity: 0.5;
    }
  }
`;
if (!document.head.querySelector('style[data-pulse]')) {
  styleSheet.setAttribute('data-pulse', 'true');
  document.head.appendChild(styleSheet);
}

const API_URL = import.meta.env.VITE_API_URL || import.meta.env.REACT_APP_API_URL || 'https://agentic-backend-lyx3.onrender.com';

export default function Dashboard() {
  const { t } = useLanguage();
  const [weatherData, setWeatherData] = useState<WeatherData | null>(null);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasRealData, setHasRealData] = useState(false);

  // Live Sensor Data State
  const [lastUpdate, setLastUpdate] = useState<string>("Never");
  const [connectionStatus, setConnectionStatus] = useState<boolean>(false);
  const [currentSensorData, setCurrentSensorData] = useState({
    temperature: 25,
    humidity: 60,
    pressure: 1013,
    wind_speed: 5,
    rainfall: 0,
    soil_moisture: 50,
    soil_temperature: 30,
    light_level: 70,
    pm25: 60,
    pm10: 120,
    uv_index: 2,
    battery_voltage: 12.5,
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        console.log('Dashboard: Fetching weather, health, and alerts...');
        const [weather, health, recentAlerts] = await Promise.all([
          getCurrentWeatherData(),
          getSystemHealth(),
          getRecentAlerts(),
        ]);
        console.log(' Weather data:', weather);
        console.log(' System health:', health);
        console.log(' Recent alerts:', recentAlerts);
        setWeatherData(weather);
        setSystemHealth(health);
        setAlerts(recentAlerts);
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : 'Failed to load data';
        setError(errMsg);
        console.error(' Error loading dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };

    // Fetch sensor data for live display and system inferences
    const fetchSensorData = async () => {
      try {
        const response = await fetch("https://agentic-backend-lyx3.onrender.com/api/sensors/latest/WS01");
        if (response.ok) {
          const data = await response.json();
          console.log(' Sensor API Response:', data);
          setConnectionStatus(true);
          const mappedData = {
            temperature: data.temperature ?? 25,
            humidity: data.humidity ?? 60,
            pressure: data.pressure ?? 1013,
            wind_speed: data.windSpeed ?? data.wind_speed ?? 5,
            rainfall: data.rainfall ?? 0,
            soil_moisture: data.soilMoisture ?? data.soil_moisture ?? 50,
            soil_temperature: data.soilTemperature ?? data.soil_temperature ?? 30,
            light_level: data.lightIntensity ?? data.light_level ?? 70,
            pm25: data.airQualityPM25 ?? data.pm25 ?? 60,
            pm10: data.airQualityPM10 ?? data.pm10 ?? 120,
            uv_index: data.uvIndex ?? data.uv_index ?? 2,
            battery_voltage: data.batteryVoltage ?? data.battery_voltage ?? 12.5,
          };
          console.log(' Mapped sensor data:', mappedData);
          setCurrentSensorData(mappedData);
          const now = new Date();
          setLastUpdate(now.toLocaleTimeString());
          console.log(' Sensor updated at:', now.toLocaleTimeString());
        } else {
          console.error(' Sensor API returned:', response.status);
          setConnectionStatus(false);
        }
      } catch (error) {
        setConnectionStatus(false);
        console.error(' Error fetching sensors:', error);
      }
    };

    // Initial fetch
    fetchData();
    fetchSensorData();

    console.log('Dashboard useEffect: Setting up polling every 10 seconds');

    // Auto-refresh ALL data every 10 seconds (now includes weatherData, health, alerts)
    const interval = setInterval(() => {
      console.log('Dashboard: Fetching fresh data...');
      fetchData();
      fetchSensorData();
    }, 10000);

    return () => {
      console.log('Dashboard: Cleaning up intervals');
      clearInterval(interval);
    };
  }, []);

  if (loading && !weatherData) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', position: 'relative' }}>
        <FarmBackground />
        <div style={{ position: 'relative', zIndex: 10 }}><WeatherLoader /></div>
      </div>
    );
  }

  if (!weatherData || !systemHealth) {
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

  // Use live sensor data for display (updates every 10 seconds), fallback to weatherData
  // Format all numbers to 2 decimal places for readability
  const displayTemp = Number(currentSensorData.temperature.toFixed(2));
  const displayHumidity = Number(currentSensorData.humidity.toFixed(2));
  const displayPressure = Number(currentSensorData.pressure.toFixed(2));
  const displayWindSpeed = Number(currentSensorData.wind_speed.toFixed(2));
  const displayRainfall = Number(currentSensorData.rainfall.toFixed(2));
  const displaySoilTemp = Number(currentSensorData.soil_temperature.toFixed(2));
  const displaySoilMoisture = Number(currentSensorData.soil_moisture.toFixed(2));
  const displayPM25 = Number(currentSensorData.pm25.toFixed(1));
  const displayPM10 = Number(currentSensorData.pm10.toFixed(1));
  const displayUVIndex = Number(currentSensorData.uv_index.toFixed(1));
  const displayLightLevel = Number(currentSensorData.light_level.toFixed(1));

  const atmosphericParams = [
    { icon: <Thermometer className="w-5 h-5" />, labelKey: 'ambient_temperature', value: displayTemp, unit: '°C', status: getParameterStatus('temperature', displayTemp) },
    { icon: <Droplets className="w-5 h-5" />, labelKey: 'relative_humidity', value: displayHumidity, unit: '%', status: getParameterStatus('humidity', displayHumidity) },
    { icon: <Gauge className="w-5 h-5" />, labelKey: 'barometric_pressure', value: displayPressure, unit: 'hPa', status: 'normal' as const },
  ];

  const windRainParams = [
    { icon: <Wind className="w-5 h-5" />, labelKey: 'wind_speed', value: displayWindSpeed, unit: 'km/h', status: getParameterStatus('windSpeed', displayWindSpeed) },
    { icon: <Compass className="w-5 h-5" />, labelKey: 'wind_direction', value: weatherData.windDirection, unit: '', status: 'normal' as const },
    { icon: <CloudRain className="w-5 h-5" />, labelKey: 'rainfall', value: displayRainfall, unit: 'mm', status: 'normal' as const },
  ];

  const radiationLightParams = [
    { icon: <Sun className="w-5 h-5" />, labelKey: 'uv_index', value: displayUVIndex, unit: '', status: getParameterStatus('uvIndex', displayUVIndex) },
    { icon: <Lightbulb className="w-5 h-5" />, labelKey: 'ambient_light', value: displayLightLevel, unit: 'lux', status: 'normal' as const },
  ];

  const airSoilParams = [
    { icon: <Cloud className="w-5 h-5" />, labelKey: 'air_quality', value: `${displayPM25}/${displayPM10}`, unit: 'µg/m³', status: getParameterStatus('airQualityPM25', displayPM25), colorClass: 'text-muted-foreground' },
    { icon: <ThermometerSun className="w-5 h-5" />, labelKey: 'soil_temperature', value: displaySoilTemp, unit: '°C', status: 'normal' as const, colorClass: 'text-soil' },
    { icon: <Waves className="w-5 h-5" />, labelKey: 'soil_moisture', value: displaySoilMoisture, unit: '%', status: getParameterStatus('soilMoisture', displaySoilMoisture), colorClass: 'text-soil' },
  ];

  return (
    <div style={{ minHeight: '100vh', position: 'relative' }}>
      <FarmBackground />
      <div style={{ position: 'relative', zIndex: 50 }}>
        <DashboardHeader lastUpdateSeconds={systemHealth.lastUpdateSeconds} sensorNodeOnline={systemHealth.sensorNodeOnline} />
      </div>

      <main style={{ position: 'relative', zIndex: 10, maxWidth: '1400px', margin: '0 auto', padding: '32px 20px 60px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>

          <GlassSection title={t('atmospheric_conditions')}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
              {atmosphericParams.map((p) => <ParameterCard key={p.labelKey} {...p} />)}
            </div>
          </GlassSection>

          <GlassSection title={t('wind_rain')}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
              {windRainParams.map((p) => <ParameterCard key={p.labelKey} {...p} />)}
            </div>
          </GlassSection>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px' }}>
            <GlassSection title={t('radiation_light')}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                {radiationLightParams.map((p) => <ParameterCard key={p.labelKey} {...p} />)}
              </div>
            </GlassSection>
            <GlassSection title={t('air_soil')}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                {airSoilParams.map((p) => <ParameterCard key={p.labelKey} {...p} colorClass={p.colorClass} />)}
              </div>
            </GlassSection>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px' }}>
            <GlassSection title="" noHeader>
              <WeatherInsightPanel />
            </GlassSection>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <SystemHealthPanel health={systemHealth} />
              <StationMapPanel />
              <AlertsPanel alerts={alerts} />
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
