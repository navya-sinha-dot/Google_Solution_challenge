import { useState, useEffect, useRef } from 'react';
import { useTheme } from 'next-themes';
import { FarmBackground, GlassSection, GlassCard } from '@/components/FarmTheme';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { useLanguage } from '@/contexts/LanguageContext';
import {
  FileText, Thermometer, Droplets, Wind, Sun,
  Sprout, CloudRain, AlertTriangle, CheckCircle, Leaf,
  Sparkles, Printer,
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.REACT_APP_API_URL || 'https://agentic-backend-lyx3.onrender.com';
const API = `${API_BASE}/api/sensors`;

interface SensorData {
  temperature: number;
  humidity: number;
  wind_speed: number;
  rainfall: number;
  soil_moisture: number;
  light: number;
  uv_index: number;
  pressure: number;
}

const defaultSensor: SensorData = {
  temperature: 0, humidity: 0, wind_speed: 0, rainfall: 0,
  soil_moisture: 0, light: 0, uv_index: 0, pressure: 0,
};

export default function Reports() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const { t } = useLanguage();
  const reportRef = useRef<HTMLDivElement>(null);

  const [sensor, setSensor] = useState<SensorData>(defaultSensor);
  const [online, setOnline] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(0);
  const [loading, setLoading] = useState(true);
  const [aiAdvice, setAiAdvice] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [reportGenerated, setReportGenerated] = useState(false);
  const [generatedAt, setGeneratedAt] = useState('');

  useEffect(() => {
    fetchSensors();
    const iv = setInterval(() => {
      fetchSensors();
      setLastUpdate((s) => s + 10);
    }, 10000);
    return () => clearInterval(iv);
  }, []);

  const fetchSensors = async () => {
    try {
      const r = await fetch(`${API}/latest/WS01`);
      if (r.ok) {
        const d = await r.json();
        setOnline(true);
        setLastUpdate(0);
        setSensor({
          temperature: Number(d.temperature) || 0,
          humidity: Number(d.humidity) || 0,
          wind_speed: Number(d.windSpeed || d.wind_speed) || 0,
          rainfall: Number(d.rainfall) || 0,
          soil_moisture: Number(d.soilMoisture || d.soil_moisture) || 0,
          light: Number(d.lightIntensity || d.light_level) || 0,
          uv_index: Number(d.uvIndex || d.uv_index) || 0,
          pressure: Number(d.pressure) || 0,
        });
      }
    } catch {
      /* ignore fetch errors */
    } finally {
      setLoading(false);
    }
  };

  const generateReport = async () => {
    setAiLoading(true);
    setAiAdvice('');
    try {
      const r = await fetch(`${API_BASE}/api/advisor/insights`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: 'overview' }),
      });
      if (r.ok) {
        const d = await r.json();
        let insights = '';
        if (typeof d.ai_insights === 'string') {
          insights = d.ai_insights;
        } else if (d.ai_insights && typeof d.ai_insights === 'object') {
          insights = d.ai_insights.summary || d.ai_insights.message || JSON.stringify(d.ai_insights);
        }
        setAiAdvice(insights || 'AI analysis complete. Conditions are within normal range.');
        if (d.sensor_data) {
          setSensor({
            temperature: Number(d.sensor_data.temperature) || sensor.temperature,
            humidity: Number(d.sensor_data.humidity) || sensor.humidity,
            wind_speed: Number(d.sensor_data.wind_speed) || sensor.wind_speed,
            rainfall: Number(d.sensor_data.rainfall) || sensor.rainfall,
            soil_moisture: Number(d.sensor_data.soil_moisture) || sensor.soil_moisture,
            light: Number(d.sensor_data.light) || sensor.light,
            uv_index: Number(d.sensor_data.uv_index) || sensor.uv_index,
            pressure: Number(d.sensor_data.pressure) || sensor.pressure,
          });
        }
      } else {
        setAiAdvice('Could not reach AI advisor. Report generated with sensor data only.');
      }
    } catch {
      setAiAdvice('Could not reach AI advisor. Report generated with sensor data only.');
    } finally {
      setAiLoading(false);
      setReportGenerated(true);
      setGeneratedAt(new Date().toLocaleString());
    }
  };

  const exportPDF = () => {
    if (!reportRef.current) return;
    const content = reportRef.current.innerHTML;
    const win = window.open('', '_blank');
    if (!win) return;
    win.document.write(`<!DOCTYPE html><html><head>
<title>Farm Report - ${new Date().toISOString().split('T')[0]}</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}
body{font-family:'Nunito',sans-serif;margin:0;padding:40px 30px;color:#1a1a1a;background:#fff;line-height:1.6}
h1,h2,h3{color:#1a1a1a!important}
p,span,div,strong{color:#1a1a1a!important}
.rpt-header{text-align:center;padding-bottom:20px;border-bottom:3px solid #2ECC71;margin-bottom:28px}
.rpt-header h1{font-size:26px;font-weight:900;color:#1a1a1a!important;margin:0 0 4px}
.rpt-header p{color:#333!important;font-size:12px;margin:2px 0}
.rpt-badge{display:inline-block;padding:3px 14px;border-radius:20px;background:#E8F5E9;color:#2E7D32!important;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:1px;margin-top:8px}
.rpt-section{margin-bottom:24px;page-break-inside:avoid}
.rpt-stitle{font-size:13px;font-weight:800;color:#2E7D32!important;text-transform:uppercase;letter-spacing:2px;margin:0 0 14px;padding-bottom:6px;border-bottom:1px solid #C8E6C9}
.rpt-footer{text-align:center;margin-top:30px;padding-top:16px;border-top:2px solid #C8E6C9;color:#555!important;font-size:10px}
@media print{body{padding:15px;color:#000!important}@page{margin:12mm;size:A4}p,span,div,h1,h2,h3,h4,strong{color:#000!important}}
</style></head><body><div style="max-width:800px;margin:0 auto">${content}</div></body></html>`);
    win.document.close();
    setTimeout(() => win.print(), 600);
  };

  // Compute statuses
  const getStatus = (type: string): string => {
    if (type === 'temp') return sensor.temperature > 35 ? 'danger' : sensor.temperature < 10 ? 'warning' : 'good';
    if (type === 'humid') return sensor.humidity > 85 ? 'warning' : sensor.humidity < 30 ? 'danger' : 'good';
    if (type === 'soil') return sensor.soil_moisture > 70 ? 'warning' : sensor.soil_moisture < 25 ? 'danger' : 'good';
    if (type === 'wind') return sensor.wind_speed > 30 ? 'danger' : sensor.wind_speed > 15 ? 'warning' : 'good';
    return 'good';
  };

  const statusColor = (s: string) => s === 'danger' ? '#E53935' : s === 'warning' ? '#FF9800' : '#4CAF50';

  const getAlerts = () => {
    const a: Array<{ severity: string; message: string; action: string }> = [];
    if (sensor.temperature > 35) a.push({ severity: 'danger', message: `High temperature: ${sensor.temperature.toFixed(1)}°C`, action: 'Provide shade and increase irrigation' });
    if (sensor.temperature < 10) a.push({ severity: 'warning', message: `Low temperature: ${sensor.temperature.toFixed(1)}°C`, action: 'Protect frost-sensitive crops' });
    if (sensor.humidity > 85) a.push({ severity: 'warning', message: `Very high humidity: ${sensor.humidity.toFixed(0)}%`, action: 'Watch for fungal diseases' });
    if (sensor.humidity < 30) a.push({ severity: 'danger', message: `Very low humidity: ${sensor.humidity.toFixed(0)}%`, action: 'Increase watering frequency' });
    if (sensor.soil_moisture < 25) a.push({ severity: 'danger', message: `Soil too dry: ${sensor.soil_moisture.toFixed(0)}%`, action: 'Irrigate immediately' });
    if (sensor.soil_moisture > 70) a.push({ severity: 'warning', message: `Soil too wet: ${sensor.soil_moisture.toFixed(0)}%`, action: 'Reduce irrigation, check drainage' });
    if (sensor.wind_speed > 30) a.push({ severity: 'danger', message: `High wind: ${sensor.wind_speed.toFixed(1)} km/h`, action: 'Secure structures, delay spraying' });
    if (sensor.rainfall > 5) a.push({ severity: 'warning', message: `Heavy rainfall: ${sensor.rainfall.toFixed(1)} mm`, action: 'Check for waterlogging' });
    if (a.length === 0) a.push({ severity: 'info', message: 'All conditions normal', action: 'Continue regular operations' });
    return a;
  };

  const sectionTitleStyle: React.CSSProperties = {
    fontSize: 14, fontWeight: 800, color: '#2E7D32',
    textTransform: 'uppercase', letterSpacing: 2,
    marginBottom: 16, paddingBottom: 8,
    borderBottom: `1px solid ${isDark ? 'rgba(46,204,113,0.2)' : '#C8E6C9'}`,
  };

  return (
    <div style={{ minHeight: '100vh', position: 'relative' }}>
      <FarmBackground />
      <div style={{ position: 'relative', zIndex: 50 }}>
        <DashboardHeader lastUpdateSeconds={lastUpdate} sensorNodeOnline={online} />
      </div>

      <main style={{ position: 'relative', zIndex: 10, maxWidth: 1400, margin: '0 auto', padding: '32px 20px 60px' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 28 }}>
          <div style={{
            width: 48, height: 48, borderRadius: 14,
            background: 'linear-gradient(135deg, #2ECC71, #1a9e52)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(46,204,113,0.35)',
          }}>
            <FileText style={{ color: 'white', width: 24, height: 24 }} />
          </div>
          <div>
            <h1 style={{ fontSize: 28, fontWeight: 800, color: isDark ? '#A8D89A' : '#1B3A20', margin: 0 }}>
              {t('reports_title')}
            </h1>
            <p style={{ fontSize: 13, color: isDark ? '#6A8A6A' : '#5A7A60', margin: 0 }}>
              {t('reports_subtitle')}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 28, flexWrap: 'wrap' }}>
          <button
            onClick={generateReport}
            disabled={aiLoading}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '14px 28px', borderRadius: 14, border: 'none',
              background: aiLoading ? '#888' : 'linear-gradient(135deg, #2ECC71, #1a9e52)',
              color: 'white', fontSize: 15, fontWeight: 800, cursor: aiLoading ? 'wait' : 'pointer',
              boxShadow: '0 4px 14px rgba(46,204,113,0.35)',
            }}
          >
            <Sparkles style={{ width: 18, height: 18 }} />
            {aiLoading ? t('reports_generating') : t('reports_generate_btn')}
          </button>

          {reportGenerated && (
            <button
              onClick={exportPDF}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '14px 24px', borderRadius: 14, border: 'none',
                background: isDark ? 'rgba(33,150,243,0.12)' : 'rgba(33,150,243,0.08)',
                color: '#2196F3', fontSize: 14, fontWeight: 800, cursor: 'pointer',
              }}
            >
              <Printer style={{ width: 16, height: 16 }} /> {t('reports_export_pdf')}
            </button>
          )}
        </div>

        {/* Loading State */}
        {aiLoading && (
          <GlassSection title="" noHeader>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, padding: '3rem' }}>
              <Sparkles style={{ width: 36, height: 36, color: '#2ECC71' }} />
              <p style={{ color: isDark ? '#A8D89A' : '#1B3A20', fontWeight: 700, fontSize: 16 }}>{t('reports_generating_msg')}</p>
              <p style={{ color: isDark ? '#5A7A5A' : '#8A9A8C', fontSize: 13 }}>{t('reports_analyzing')}</p>
            </div>
          </GlassSection>
        )}

        {/* Generated Report */}
        {reportGenerated && !aiLoading && (
          <div ref={reportRef}>
            {/* Report Header */}
            <div className="rpt-header" style={{
              textAlign: 'center', paddingBottom: 24,
              borderBottom: '3px solid #2ECC71', marginBottom: 32,
            }}>
              <h1 style={{ fontSize: 26, fontWeight: 900, color: isDark ? '#A8D89A' : '#1B3A20', margin: '0 0 4px' }}>
                Daily Farm Intelligence Report
              </h1>
              <p style={{ color: isDark ? '#6A8A6A' : '#5A7A60', fontSize: 13, margin: '2px 0' }}>
                Station: WS01 • {generatedAt}
              </p>
              <span className="rpt-badge" style={{
                display: 'inline-block', padding: '4px 16px', borderRadius: 20,
                background: 'rgba(46,204,113,0.12)', color: '#2E7D32',
                fontSize: 11, fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1, marginTop: 10,
              }}>
                AI-Verified • Live Sensor Data
              </span>
            </div>

            {/* Section 1: Weather */}
            <div style={{ marginBottom: 28 }}>
              <h2 style={sectionTitleStyle}>️ Weather &amp; Environment Overview</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12 }}>
                {[
                  { label: 'Temperature', val: sensor.temperature.toFixed(1), unit: '°C', status: getStatus('temp'), Icon: Thermometer },
                  { label: 'Humidity', val: sensor.humidity.toFixed(0), unit: '%', status: getStatus('humid'), Icon: Droplets },
                  { label: 'Wind Speed', val: sensor.wind_speed.toFixed(1), unit: 'km/h', status: getStatus('wind'), Icon: Wind },
                  { label: 'Rainfall', val: sensor.rainfall.toFixed(1), unit: 'mm', status: sensor.rainfall > 5 ? 'warning' : 'good', Icon: CloudRain },
                  { label: 'Pressure', val: sensor.pressure.toFixed(0), unit: 'hPa', status: 'good', Icon: Sun },
                  { label: 'UV Index', val: sensor.uv_index.toFixed(1), unit: '', status: sensor.uv_index > 8 ? 'danger' : 'good', Icon: Sun },
                ].map((m) => (
                  <GlassCard key={m.label}>
                    <div style={{ textAlign: 'center' }}>
                      <m.Icon style={{ width: 16, height: 16, color: statusColor(m.status), marginBottom: 6 }} />
                      <p style={{ fontSize: 9, fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1, color: isDark ? '#5A7A5A' : '#8A9A8C', marginBottom: 4 }}>{m.label}</p>
                      <p style={{ fontSize: 24, fontWeight: 900, color: isDark ? '#C8E8C8' : '#1B3A20', margin: 0 }}>
                        {m.val}<span style={{ fontSize: 11, color: '#4CAF50', fontWeight: 700, marginLeft: 2 }}>{m.unit}</span>
                      </p>
                      <div style={{ width: 8, height: 8, borderRadius: '50%', background: statusColor(m.status), margin: '6px auto 0', boxShadow: `0 0 6px ${statusColor(m.status)}` }} />
                    </div>
                  </GlassCard>
                ))}
              </div>
            </div>

            {/* Section 2: Soil & Crop */}
            <div style={{ marginBottom: 28 }}>
              <h2 style={sectionTitleStyle}> Soil &amp; Crop Health</h2>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <GlassCard>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div style={{ padding: 12, borderRadius: 12, background: `${statusColor(getStatus('soil'))}15` }}>
                      <Sprout style={{ width: 22, height: 22, color: statusColor(getStatus('soil')) }} />
                    </div>
                    <div>
                      <p style={{ fontSize: 9, fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1.2, color: isDark ? '#5A7A5A' : '#8A9A8C' }}>Soil Moisture</p>
                      <p style={{ fontSize: 28, fontWeight: 900, color: isDark ? '#C8E8C8' : '#1B3A20', margin: 0 }}>{sensor.soil_moisture.toFixed(0)}%</p>
                      <p style={{ fontSize: 11, color: statusColor(getStatus('soil')), fontWeight: 700 }}>
                        {getStatus('soil') === 'danger' ? '️ Critically Low' : getStatus('soil') === 'warning' ? ' Too Wet' : ' Optimal'}
                      </p>
                    </div>
                  </div>
                </GlassCard>
                <GlassCard>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div style={{ padding: 12, borderRadius: 12, background: 'rgba(255,152,0,0.1)' }}>
                      <Sun style={{ width: 22, height: 22, color: '#FF9800' }} />
                    </div>
                    <div>
                      <p style={{ fontSize: 9, fontWeight: 800, textTransform: 'uppercase', letterSpacing: 1.2, color: isDark ? '#5A7A5A' : '#8A9A8C' }}>Light Intensity</p>
                      <p style={{ fontSize: 28, fontWeight: 900, color: isDark ? '#C8E8C8' : '#1B3A20', margin: 0 }}>{sensor.light.toFixed(0)}</p>
                      <p style={{ fontSize: 11, color: '#FF9800', fontWeight: 700 }}>
                        {sensor.light > 50000 ? '️ Very Bright' : sensor.light > 10000 ? '️ Good Light' : '️ Low Light'}
                      </p>
                    </div>
                  </div>
                </GlassCard>
              </div>
            </div>

            {/* Section 3: Irrigation */}
            <div style={{ marginBottom: 28 }}>
              <h2 style={sectionTitleStyle}> Irrigation Recommendation</h2>
              <GlassCard>
                <div style={{ padding: '8px 0' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                    <Droplets style={{ width: 20, height: 20, color: '#2196F3' }} />
                    <span style={{ fontSize: 16, fontWeight: 800, color: isDark ? '#C8E8C8' : '#1B3A20' }}>
                      {sensor.soil_moisture < 30 ? ' Irrigate Now' : sensor.soil_moisture < 45 ? '🟡 Schedule Irrigation' : '🟢 No Irrigation Needed'}
                    </span>
                  </div>
                  <p style={{ fontSize: 13, color: isDark ? '#A8D89A' : '#333', lineHeight: 1.7 }}>
                    {sensor.soil_moisture < 30
                      ? `Soil moisture is critically low at ${sensor.soil_moisture.toFixed(0)}%. Immediate irrigation recommended. Estimated water need: ${Math.round((50 - sensor.soil_moisture) * 8)} liters/acre.`
                      : sensor.soil_moisture < 45
                        ? `Soil moisture at ${sensor.soil_moisture.toFixed(0)}%, approaching lower threshold. Schedule irrigation within 6-12 hours. Best time: early morning or late evening.`
                        : `Soil moisture at a healthy ${sensor.soil_moisture.toFixed(0)}%. No immediate irrigation needed. Next check in 12 hours.`
                    }
                  </p>
                  {sensor.rainfall > 0 && (
                    <p style={{ fontSize: 12, color: '#2196F3', fontWeight: 600, marginTop: 8 }}>
                      Recent rainfall of {sensor.rainfall.toFixed(1)} mm detected — factor into irrigation schedule.
                    </p>
                  )}
                </div>
              </GlassCard>
            </div>

            {/* Section 4: Alerts */}
            <div style={{ marginBottom: 28 }}>
              <h2 style={sectionTitleStyle}> Active Alerts &amp; Warnings</h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {getAlerts().map((alert, idx) => (
                  <GlassCard key={idx}>
                    <div style={{ borderLeft: `4px solid ${alert.severity === 'danger' ? '#E53935' : alert.severity === 'warning' ? '#FF9800' : '#4CAF50'}`, paddingLeft: 14 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                        {alert.severity === 'info'
                          ? <CheckCircle style={{ width: 16, height: 16, color: '#4CAF50' }} />
                          : <AlertTriangle style={{ width: 16, height: 16, color: alert.severity === 'danger' ? '#E53935' : '#FF9800' }} />
                        }
                        <span style={{ fontSize: 14, fontWeight: 700, color: isDark ? '#C8E8C8' : '#1B3A20' }}>{alert.message}</span>
                      </div>
                      <p style={{ fontSize: 12, color: isDark ? '#7A9A7A' : '#5A7A60', margin: 0 }}>
                        <strong>Action:</strong> {alert.action}
                      </p>
                    </div>
                  </GlassCard>
                ))}
              </div>
            </div>

            {/* Section 5: AI Insights */}
            {aiAdvice && (
              <div style={{ marginBottom: 28 }}>
                <h2 style={sectionTitleStyle}> AI Farm Advisor Insights</h2>
                <GlassCard>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                    <div style={{ padding: 10, borderRadius: 12, background: 'linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.12))', flexShrink: 0 }}>
                      <Sparkles style={{ width: 20, height: 20, color: '#7C3AED' }} />
                    </div>
                    <div>
                      <p style={{ fontSize: 11, fontWeight: 800, color: '#7C3AED', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>
                        Powered by Groq AI • Live Analysis
                      </p>
                      <p style={{ fontSize: 13, color: isDark ? '#C8E8C8' : '#333', lineHeight: 1.8, whiteSpace: 'pre-line' }}>
                        {aiAdvice}
                      </p>
                    </div>
                  </div>
                </GlassCard>
              </div>
            )}

            {/* Section 6: Action Plan */}
            <div style={{ marginBottom: 28 }}>
              <h2 style={sectionTitleStyle}> Today&apos;s Action Plan</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 12 }}>
                {[
                  { time: ' Morning (6-9 AM)', task: sensor.soil_moisture < 40 ? 'Start irrigation — soil needs water' : 'Inspect crops, check for overnight damage' },
                  { time: '️ Midday (10-2 PM)', task: sensor.temperature > 32 ? 'Provide shade, avoid field work in heat' : 'Good conditions for field operations' },
                  { time: '️ Afternoon (3-6 PM)', task: sensor.humidity > 70 ? 'Monitor for fungal conditions' : 'Apply fertilizers if needed' },
                  { time: ' Evening', task: 'Review data, plan tomorrow, check forecast' },
                ].map((item, idx) => (
                  <GlassCard key={idx}>
                    <p style={{ fontSize: 12, fontWeight: 800, color: '#2E7D32', marginBottom: 6 }}>{item.time}</p>
                    <p style={{ fontSize: 12, color: isDark ? '#A8D89A' : '#333', lineHeight: 1.5, margin: 0 }}>{item.task}</p>
                  </GlassCard>
                ))}
              </div>
            </div>

            {/* Footer */}
            <div className="rpt-footer" style={{
              textAlign: 'center', marginTop: 40, paddingTop: 20,
              borderTop: `2px solid ${isDark ? 'rgba(46,204,113,0.15)' : '#C8E6C9'}`,
              color: isDark ? '#5A7A5A' : '#7A9A7A', fontSize: 11,
            }}>
              <p style={{ margin: '4px 0' }}><strong>© {new Date().getFullYear()} AgriSense AI Farm Intelligence System</strong></p>
              <p style={{ margin: '4px 0' }}>Report from live IoT sensors • AI analysis by Groq LLM</p>
              <p style={{ margin: '4px 0', opacity: 0.6 }}>Report ID: RPT-{Math.random().toString(36).substr(2, 8).toUpperCase()}</p>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!reportGenerated && !aiLoading && (
          <GlassSection title="" noHeader>
            <div style={{ padding: '60px 20px', textAlign: 'center' }}>
              <div style={{
                width: 80, height: 80, borderRadius: '50%', margin: '0 auto 24px',
                background: isDark ? 'rgba(46,204,113,0.08)' : 'rgba(46,204,113,0.05)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <FileText style={{ width: 40, height: 40, color: isDark ? '#3A5A3A' : '#C0D0C0' }} />
              </div>
              <h3 style={{ fontSize: 20, fontWeight: 800, color: isDark ? '#A8D89A' : '#1B3A20', marginBottom: 8 }}>
                {t('reports_ready_title')}
              </h3>
              <p style={{ color: isDark ? '#5A7A5A' : '#8A9A8C', fontSize: 14, maxWidth: 400, margin: '0 auto 24px', lineHeight: 1.6 }}>
                {t('reports_ready_desc')}
              </p>
              <div style={{ display: 'flex', justifyContent: 'center', gap: 12, flexWrap: 'wrap' }}>
                {['️ Weather', ' Soil Health', ' Irrigation', ' Alerts', ' AI Advice', ' Plan'].map((item, i) => (
                  <span key={i} style={{
                    fontSize: 12, fontWeight: 700, color: isDark ? '#6A8A6A' : '#5A7A60',
                    padding: '6px 14px', borderRadius: 20,
                    background: isDark ? 'rgba(46,204,113,0.06)' : 'rgba(46,204,113,0.04)',
                  }}>
                    {item}
                  </span>
                ))}
              </div>
            </div>
          </GlassSection>
        )}
      </main>
    </div>
  );
}
