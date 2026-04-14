import { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import { FarmBackground, GlassSection, GlassCard } from "@/components/FarmTheme";
import { DashboardHeader } from "@/components/dashboard/DashboardHeader";
import { Droplets, Sprout, Wind, Thermometer, Leaf, Loader2, Sparkles, RefreshCw, CheckCircle2 } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

export default function Advisor() {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const { t } = useLanguage();

  // Live sensor data from backend
  const [sensorData, setSensorData] = useState({ temperature: 0, humidity: 0, wind_speed: 0, rainfall: 0, soil_moisture: 0, light: 0, uv_index: 0, pressure: 0 });
  const [sensorOnline, setSensorOnline] = useState(false);
  const [lastUpdateSec, setLastUpdateSec] = useState(0);

  // AI insights
  const [overview, setOverview] = useState<{ summary: string; focus_points: string[]; details?: string } | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch live sensor data on mount + interval
  useEffect(() => {
    fetchSensorData();
    const iv = setInterval(() => {
      fetchSensorData();
      setLastUpdateSec((s) => s + 10);
    }, 10000);
    return () => clearInterval(iv);
  }, []);

  // Initial AI overview fetch
  useEffect(() => {
    fetchAIOverview();
  }, []);

  const fetchSensorData = async () => {
    try {
      const r = await fetch("http://localhost:8000/api/sensors/latest/WS01");
      if (r.ok) {
        const d = await r.json();
        setSensorOnline(true);
        setLastUpdateSec(0);
        setSensorData({
          temperature: d.temperature || 0,
          humidity: d.humidity || 0,
          wind_speed: d.windSpeed || d.wind_speed || 0,
          rainfall: d.rainfall || 0,
          soil_moisture: d.soilMoisture || d.soil_moisture || 0,
          light: d.lightIntensity || d.light_level || 0,
          uv_index: d.uvIndex || d.uv_index || 0,
          pressure: d.pressure || 0,
        });
      }
    } catch {
      setSensorOnline(false);
    }
  };

  const fetchAIOverview = async () => {
    setIsLoading(true);
    try {
      const r = await fetch("http://localhost:8000/api/advisor/insights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category: "overview" }),
      });
      if (r.ok) {
        const data = await r.json();
        setOverview(data.ai_insights);
        if (data.sensor_data) {
          setSensorData(data.sensor_data);
          setSensorOnline(true);
          setLastUpdateSec(0);
        }
      }
    } catch (e) {
      console.error("Advisor fetch error:", e);
    } finally {
      setIsLoading(false);
    }
  };

  const weatherStats = [
    { icon: <Thermometer style={{ width: 20, height: 20 }} />, label: t('temperature'), value: `${sensorData.temperature.toFixed(1)}°C`, color: "#E53935" },
    { icon: <Droplets style={{ width: 20, height: 20 }} />, label: t('humidity'), value: `${sensorData.humidity.toFixed(0)}%`, color: "#2196F3" },
    { icon: <Wind style={{ width: 20, height: 20 }} />, label: t('wind_speed'), value: `${sensorData.wind_speed.toFixed(1)} km/h`, color: "#00BCD4" },
    { icon: <Sprout style={{ width: 20, height: 20 }} />, label: t('soil_moisture'), value: `${sensorData.soil_moisture.toFixed(0)}%`, color: "#4CAF50" },
  ];

  return (
    <div style={{ minHeight: "100vh", position: "relative" }}>
      <FarmBackground />
      <div style={{ position: "relative", zIndex: 50 }}>
        <DashboardHeader lastUpdateSeconds={lastUpdateSec} sensorNodeOnline={sensorOnline} />
      </div>

      <main style={{ position: "relative", zIndex: 10, maxWidth: "1000px", margin: "0 auto", padding: "32px 20px 60px" }}>
        {/* Page Header */}
        <div style={{ marginBottom: 32, textAlign: "center" }}>

          <h1 style={{ fontSize: 32, fontWeight: 800, fontFamily: "'Nunito', sans-serif", color: isDark ? "#A8D89A" : "#0a1c0dff", marginBottom: 8 }}>
            {t('advisor_title')}
          </h1>
          <p style={{ fontSize: 15, color: isDark ? "#6A8A6A" : "#081d0cff", maxWidth: "600px", margin: "0 auto" }}>
            {t('advisor_subtitle')}
          </p>
        </div>

        {/* Live Weather Stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 32 }}>
          {weatherStats.map((stat, i) => (
            <GlassCard key={i}>
              <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                <div style={{ padding: 10, borderRadius: 12, background: `${stat.color}15`, color: stat.color }}>
                  {stat.icon}
                </div>
                <div>
                  <p style={{ fontSize: 10, fontWeight: 800, textTransform: "uppercase", letterSpacing: "1.2px", color: isDark ? "#5A7A5A" : "#8A9A8C" }}>{stat.label}</p>
                  <p style={{ fontSize: 22, fontWeight: 900, color: isDark ? "#C8E8C8" : "#1B3A20", fontVariantNumeric: "tabular-nums" }}>{stat.value}</p>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>

        {/* Advisor Overview */}
        <GlassSection title="" noHeader>
          <div style={{ padding: "8px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24, borderBottom: `1px solid ${isDark ? "rgba(46,204,113,0.1)" : "rgba(46,204,113,0.1)"}`, paddingBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#2ECC71", boxShadow: "0 0 8px #2ECC71" }} />
                <span style={{ fontSize: 14, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1, color: isDark ? "#A8D89A" : "#1B3A20" }}>{t('advisor_current')}</span>
              </div>
              <button
                onClick={fetchAIOverview}
                disabled={isLoading}
                style={{
                  display: "flex", alignItems: "center", gap: 8, padding: "8px 16px", borderRadius: 12, border: "none",
                  background: isDark ? "rgba(46,204,113,0.1)" : "rgba(46,204,113,0.08)", color: "#2ECC71",
                  fontSize: 13, fontWeight: 700, cursor: "pointer", transition: "all 0.2s"
                }}
              >
                <RefreshCw style={{ width: 14, height: 14, animation: isLoading ? "spin 1s linear infinite" : "none" }} />
                {isLoading ? t('advisor_analyzing') : t('advisor_refresh')}
              </button>
            </div>

            {isLoading ? (
              <div style={{ textAlign: "center", padding: "60px 20px" }}>
                <Loader2 style={{ width: 48, height: 48, color: "#2ECC71", animation: "spin 1s linear infinite", margin: "0 auto 20px" }} />
                <h3 style={{ fontSize: 20, fontWeight: 700, color: isDark ? "#C8E8C8" : "#1B3A20", marginBottom: 8 }}>{t('advisor_ai_analyzing')}</h3>
                <p style={{ color: isDark ? "#6A8A6A" : "#5A7A60" }}>{t('advisor_processing')}</p>
              </div>
            ) : (
              <div style={{ padding: "10px 10px" }}>
                {overview && typeof overview === "object" ? (
                  <>
                    <div style={{ marginBottom: 32 }}>
                      <p style={{ fontSize: 18, lineHeight: 1.8, color: isDark ? "#C8E8C8" : "#333", fontWeight: 500 }} dangerouslySetInnerHTML={{ __html: overview.summary }} />
                    </div>

                    {overview.details && (
                      <div style={{ marginBottom: 24 }}>
                        <p style={{ fontSize: 15, lineHeight: 1.8, color: isDark ? "#E5E7EB" : "#444", fontWeight: 400 }} dangerouslySetInnerHTML={{ __html: overview.details }} />
                      </div>
                    )}

                    {overview.focus_points && Array.isArray(overview.focus_points) && (
                      <div>
                        <h3 style={{ fontSize: 16, fontWeight: 800, color: "#2ECC71", textTransform: "uppercase", letterSpacing: 1, marginBottom: 16 }}>{t('advisor_focus')}</h3>
                        <div style={{ display: "grid", gap: 12 }}>
                          {overview.focus_points.map((point, i) => (
                            <div key={i} style={{ display: "flex", gap: 14, padding: "16px", borderRadius: 16, background: isDark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)", border: `1px solid ${isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)"}` }}>
                              <CheckCircle2 style={{ width: 20, height: 20, color: "#2ECC71", flexShrink: 0 }} />
                              <p style={{ fontSize: 14, color: isDark ? "#A8D89A" : "#333", lineHeight: 1.5 }}>{point}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div style={{ textAlign: "center", padding: "40px" }}>
                    <p style={{ color: isDark ? "#6A8A6A" : "#5A7A60" }}>{typeof overview === 'string' ? overview : t('advisor_no_data')}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </GlassSection>
      </main>

      {/* CSS for spin animation */}
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
