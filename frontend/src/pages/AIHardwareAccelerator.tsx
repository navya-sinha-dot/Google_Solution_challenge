import { useState, useEffect, useRef } from "react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { CloudRain, Leaf, Droplets, Cpu, Wifi, WifiOff } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { DashboardHeader } from "@/components/dashboard/DashboardHeader";
import { FarmBackground, GlassSection } from "@/components/FarmTheme";
import { useLanguage } from "@/contexts/LanguageContext";

export default function AIHardwareAccelerator() {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const { toast } = useToast();
  const { t } = useLanguage();
  const [loadingRain, setLoadingRain] = useState(false);
  const [loadingFusion, setLoadingFusion] = useState(false);
  const [loadingCombined, setLoadingCombined] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [rainPrediction, setRainPrediction] = useState<any>(null);
  const [sensorFusion, setSensorFusion] = useState<any>(null);
  const [combinedAnalysis, setCombinedAnalysis] = useState<any>(null);
  const [lastUpdate, setLastUpdate] = useState<string>("Never");
  const [connectionStatus, setConnectionStatus] = useState<boolean>(false);
  const [lastUpdateSeconds, setLastUpdateSeconds] = useState(0);
  const [hardwareStatus, setHardwareStatus] = useState<{
    mode: string;
    port: string | null;
    fpga_enabled: boolean;
  }>({ mode: "unknown", port: null, fpga_enabled: false });
  const [currentSensorData, setCurrentSensorData] = useState({
    temperature: 25,
    humidity: 60,
    pressure: 1013,
    wind_speed: 5,
    rainfall: 0,
    soil_moisture: 50,
    soil_temperature: 26,
    light_level: 70,
    pm25: 60,
    pm10: 120,
    uv_index: 2,
    battery_voltage: 12.5,
  });

  // ─── Floating particle animation ───────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const resize = () => {
      const rect = canvas.parentElement!.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);

    const agents = [
      { name: "Supervisor", emoji: "" },
      { name: "Trend", emoji: "" },
      { name: "Output", emoji: "" },
      { name: "Ingress", emoji: "" },
      { name: "Health", emoji: "" },
      { name: "Alert", emoji: "" },
      { name: "Weather", emoji: "️" },
      { name: "Response", emoji: "" },
    ];

    interface Particle {
      x: number; y: number;
      vx: number; vy: number;
      radius: number;
      name: string; emoji: string;
      glowPhase: number;
      trail: { x: number; y: number }[];
      isDragged?: boolean;
    }

    const w = () => canvas.width / dpr;
    const h = () => canvas.height / dpr;

    const particles: Particle[] = agents.map((a, i) => ({
      x: Math.random() * (w() - 120) + 60,
      y: Math.random() * (h() - 120) + 60,
      vx: (Math.random() - 0.5) * 0.6,
      vy: (Math.random() - 0.5) * 0.6,
      radius: 28,
      name: a.name,
      emoji: a.emoji,
      glowPhase: (i / agents.length) * Math.PI * 2,
      trail: [],
      isDragged: false,
    }));

    let draggedParticle: Particle | null = null;

    const onMouseDown = (e: MouseEvent) => {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        const dx = p.x - mx;
        const dy = p.y - my;
        if (dx * dx + dy * dy <= p.radius * p.radius) {
          draggedParticle = p;
          p.isDragged = true;
          canvas.style.cursor = "grabbing";
          break;
        }
      }
    };

    const onMouseMove = (e: MouseEvent) => {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      if (draggedParticle) {
        draggedParticle.x = mx;
        draggedParticle.y = my;
        draggedParticle.vx = 0;
        draggedParticle.vy = 0;
      } else {
        let hovered = false;
        for (let p of particles) {
          const dx = p.x - mx;
          const dy = p.y - my;
          if (dx * dx + dy * dy <= p.radius * p.radius) {
            hovered = true;
            break;
          }
        }
        canvas.style.cursor = hovered ? "grab" : "default";
      }
    };

    const onMouseUp = () => {
      if (draggedParticle) {
        draggedParticle.isDragged = false;
        draggedParticle = null;
        if (canvas) canvas.style.cursor = "grab";
      }
    };

    const onMouseLeave = () => {
      if (draggedParticle) {
        draggedParticle.isDragged = false;
        draggedParticle = null;
        if (canvas) canvas.style.cursor = "default";
      }
    };

    canvas.addEventListener("mousedown", onMouseDown);
    canvas.addEventListener("mousemove", onMouseMove);
    canvas.addEventListener("mouseup", onMouseUp);
    canvas.addEventListener("mouseleave", onMouseLeave);

    let animId: number;
    let tick = 0;

    const draw = () => {
      tick++;
      const W = w(), H = h();
      const cx = W / 2, cy = H / 2;

      ctx.clearRect(0, 0, W, H);

      // Draw lines from each particle to center (Orchestrator)
      particles.forEach((p) => {
        const glow = 0.15 + Math.sin(tick * 0.02 + p.glowPhase) * 0.1;
        const grad = ctx.createLinearGradient(cx, cy, p.x, p.y);
        grad.addColorStop(0, `rgba(46, 204, 113, ${glow + 0.3})`);
        grad.addColorStop(1, `rgba(46, 204, 113, ${glow})`);
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(p.x, p.y);
        ctx.strokeStyle = grad;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Animated data pulse along line
        const pulsePos = ((tick * 2 + p.glowPhase * 50) % 100) / 100;
        const px = cx + (p.x - cx) * pulsePos;
        const py = cy + (p.y - cy) * pulsePos;
        ctx.beginPath();
        ctx.arc(px, py, 3, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(46, 204, 113, ${0.8 - pulsePos * 0.5})`;
        ctx.fill();
      });

      // Update & draw particles
      particles.forEach((p) => {
        if (!p.isDragged) {
          // Soft boundary repulsion
          if (p.x < 50) p.vx += 0.03;
          if (p.x > W - 50) p.vx -= 0.03;
          if (p.y < 50) p.vy += 0.03;
          if (p.y > H - 50) p.vy -= 0.03;

          // Gentle random drift
          p.vx += (Math.random() - 0.5) * 0.02;
          p.vy += (Math.random() - 0.5) * 0.02;

          // Damping
          p.vx *= 0.995;
          p.vy *= 0.995;

          // Speed limit
          const speed = Math.sqrt(p.vx * p.vx + p.vy * p.vy);
          if (speed > 1) { p.vx *= 1 / speed; p.vy *= 1 / speed; }

          p.x += p.vx;
          p.y += p.vy;
        } else {
          p.vx = 0;
          p.vy = 0;
        }

        // Trail
        p.trail.push({ x: p.x, y: p.y });
        if (p.trail.length > 12) p.trail.shift();

        // Draw trail
        for (let i = 0; i < p.trail.length - 1; i++) {
          const alpha = (i / p.trail.length) * 0.2;
          ctx.beginPath();
          ctx.arc(p.trail[i].x, p.trail[i].y, 2, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(46, 204, 113, ${alpha})`;
          ctx.fill();
        }

        // Glow
        const glowSize = 38 + Math.sin(tick * 0.03 + p.glowPhase) * 6;
        const grd = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, glowSize);
        grd.addColorStop(0, "rgba(46, 204, 113, 0.25)");
        grd.addColorStop(1, "rgba(46, 204, 113, 0)");
        ctx.beginPath();
        ctx.arc(p.x, p.y, glowSize, 0, Math.PI * 2);
        ctx.fillStyle = grd;
        ctx.fill();

        // Particle circle
        const pgrd = ctx.createRadialGradient(p.x - 6, p.y - 6, 2, p.x, p.y, p.radius);
        pgrd.addColorStop(0, "rgba(39, 174, 96, 0.95)");
        pgrd.addColorStop(1, "rgba(13, 59, 27, 0.95)");
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = pgrd;
        ctx.fill();
        ctx.strokeStyle = "rgba(46, 204, 113, 0.4)";
        ctx.lineWidth = 1;
        ctx.stroke();

        // Emoji & Name
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        if (p.emoji) {
          ctx.font = "14px sans-serif";
          ctx.fillText(p.emoji, p.x, p.y - 8);
          ctx.font = "bold 10px 'Inter', sans-serif";
          ctx.fillStyle = "#FFFFFF";
          ctx.fillText(p.name, p.x, p.y + 8);
        } else {
          ctx.font = "bold 10px 'Inter', sans-serif";
          ctx.fillStyle = "#FFFFFF";
          ctx.fillText(p.name, p.x, p.y);
        }
      });

      // Central Orchestrator with pulse
      const oGlow = 48 + Math.sin(tick * 0.025) * 10;
      const ogrd = ctx.createRadialGradient(cx, cy, 0, cx, cy, oGlow);
      ogrd.addColorStop(0, "rgba(46, 204, 113, 0.35)");
      ogrd.addColorStop(0.6, "rgba(46, 204, 113, 0.1)");
      ogrd.addColorStop(1, "rgba(46, 204, 113, 0)");
      ctx.beginPath();
      ctx.arc(cx, cy, oGlow, 0, Math.PI * 2);
      ctx.fillStyle = ogrd;
      ctx.fill();

      // Outer ring
      ctx.beginPath();
      ctx.arc(cx, cy, 36, 0, Math.PI * 2);
      const coreGrd = ctx.createRadialGradient(cx - 8, cy - 8, 3, cx, cy, 36);
      coreGrd.addColorStop(0, "#2ECC71");
      coreGrd.addColorStop(1, "#1B5E20");
      ctx.fillStyle = coreGrd;
      ctx.fill();
      ctx.strokeStyle = "rgba(46, 204, 113, 0.5)";
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.font = "bold 11px 'Inter', sans-serif";
      ctx.fillStyle = "#FFFFFF";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("Orchestrator", cx, cy);

      animId = requestAnimationFrame(draw);
    };

    draw();
    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
      canvas.removeEventListener("mousedown", onMouseDown);
      canvas.removeEventListener("mousemove", onMouseMove);
      canvas.removeEventListener("mouseup", onMouseUp);
      canvas.removeEventListener("mouseleave", onMouseLeave);
    };
  }, []);

  // ─── Data fetching ─────────────────────────────────────────────
  useEffect(() => {
    fetchSensorData();
    fetchHardwareStatus();
    const interval = setInterval(() => {
      fetchSensorData();
      setLastUpdateSeconds((s) => s + 10);
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchHardwareStatus = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/fpga/status");
      if (response.ok) {
        const data = await response.json();
        setHardwareStatus({
          mode: data.hardware_mode || "unknown",
          port: data.port || null,
          fpga_enabled: data.fpga_enabled || false,
        });
      }
    } catch {
      setHardwareStatus({ mode: "disconnected", port: null, fpga_enabled: false });
    }
  };

  const fetchSensorData = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/sensors/latest/WS01");
      if (response.ok) {
        const data = await response.json();
        setConnectionStatus(true);
        setLastUpdateSeconds(0);
        setCurrentSensorData({
          temperature: data.temperature ?? 25,
          humidity: data.humidity ?? 60,
          pressure: data.pressure ?? 1013,
          wind_speed: data.windSpeed ?? data.wind_speed ?? 5,
          rainfall: data.rainfall ?? 0,
          soil_moisture: data.soilMoisture ?? data.soil_moisture ?? 50,
          soil_temperature: data.soilTemperature ?? data.soil_temperature ?? 26,
          light_level: data.lightIntensity ?? data.light_level ?? 70,
          pm25: data.airQualityPM25 ?? data.pm25 ?? 60,
          pm10: data.airQualityPM10 ?? data.pm10 ?? 120,
          uv_index: data.uvIndex ?? data.uv_index ?? 2,
          battery_voltage: data.batteryVoltage ?? data.battery_voltage ?? 12.5,
        });
        setLastUpdate(new Date().toLocaleTimeString());
      }
    } catch {
      setConnectionStatus(false);
    }
  };

  // ─── FPGA actions ──────────────────────────────────────────────
  const predictRain = async () => {
    setLoadingRain(true);
    try {
      const response = await fetch("http://localhost:8000/api/fpga/rain-predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          temperature: currentSensorData.temperature,
          humidity: currentSensorData.humidity,
          pressure: currentSensorData.pressure,
          wind_speed: currentSensorData.wind_speed,
        }),
      });
      if (response.ok) {
        const data = await response.json();
        setRainPrediction(data);
        if (data.hardware_mode) setHardwareStatus((p) => ({ ...p, mode: data.hardware_mode }));
        toast({ title: " Rain Prediction Complete", description: `${data.prediction.rain_probability}% via ${data.hardware_mode === "real_hardware" ? "COM4" : "ML Model Cache"}` });
      } else {
        toast({ title: " Prediction Failed", description: "Could not reach FPGA", variant: "destructive" });
      }
    } catch {
      toast({ title: " Error", description: "Connection to backend failed", variant: "destructive" });
    } finally {
      setLoadingRain(false);
    }
  };

  const runSensorFusion = async () => {
    setLoadingFusion(true);
    try {
      const response = await fetch("http://localhost:8000/api/fpga/fusion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          soil_moisture: currentSensorData.soil_moisture,
          temperature: currentSensorData.temperature,
          humidity: currentSensorData.humidity,
          light_level: currentSensorData.light_level,
        }),
      });
      if (response.ok) {
        const data = await response.json();
        setSensorFusion(data);
        if (data.hardware_mode) setHardwareStatus((p) => ({ ...p, mode: data.hardware_mode }));
        toast({ title: "Crop Health Analysis Complete", description: `via ${data.hardware_mode === "real_hardware" ? "COM4 Hardware" : "ML Prediction Cache"}` });
      } else {
        toast({ title: " Analysis Failed", variant: "destructive" });
      }
    } catch {
      toast({ title: " Error", description: "Connection failed", variant: "destructive" });
    } finally {
      setLoadingFusion(false);
    }
  };

  const runCombinedAnalysis = async () => {
    setLoadingCombined(true);
    try {
      const response = await fetch("http://localhost:8000/api/fpga/combined-analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          soil_moisture: currentSensorData.soil_moisture,
          temperature: currentSensorData.temperature,
          humidity: currentSensorData.humidity,
          light_level: currentSensorData.light_level,
        }),
      });
      if (response.ok) {
        const data = await response.json();
        setCombinedAnalysis(data);
        if (data.hardware_mode) setHardwareStatus((p) => ({ ...p, mode: data.hardware_mode }));
        toast({ title: "Irrigation Analysis Complete" });
      } else {
        toast({ title: " Analysis Failed", variant: "destructive" });
      }
    } catch {
      toast({ title: " Error", description: "Connection failed", variant: "destructive" });
    } finally {
      setLoadingCombined(false);
    }
  };

  const getRiskColor = (probability: number) => {
    if (probability >= 80) return { bg: "#FEE2E2", text: "#DC2626" };
    if (probability >= 60) return { bg: "#FED7AA", text: "#EA580C" };
    if (probability >= 40) return { bg: "#FEF3C7", text: "#D97706" };
    if (probability >= 20) return { bg: "#DBEAFE", text: "#2563EB" };
    return { bg: "#DCFCE7", text: "#16A34A" };
  };

  const hwBadge = hardwareStatus.mode === "real_hardware"
    ? { label: t('accel_connected'), color: "#2ECC71", bg: "rgba(46,204,113,0.15)", icon: <Wifi style={{ width: 14, height: 14 }} /> }
    : hardwareStatus.mode === "simulation"
      ? { label: t('accel_simulation'), color: "#F59E0B", bg: "rgba(245,158,11,0.15)", icon: <Cpu style={{ width: 14, height: 14 }} /> }
      : { label: t('accel_disconnected'), color: "#EF4444", bg: "rgba(239,68,68,0.15)", icon: <WifiOff style={{ width: 14, height: 14 }} /> };

  const modeBadge = (mode?: string) => (
    <span style={{
      fontSize: "0.7rem", padding: "0.2rem 0.6rem", borderRadius: 9999,
      backgroundColor: mode === "real_hardware" ? "rgba(46,204,113,0.2)" : "rgba(245,158,11,0.2)",
      color: mode === "real_hardware" ? "#2ECC71" : "#F59E0B",
    }}>
      {mode === "real_hardware" ? t('accel_hardware') : t('accel_simulation')}
    </span>
  );

  // ─── Render ────────────────────────────────────────────────────
  return (
    <div style={{ minHeight: "100vh", position: "relative" }}>
      <FarmBackground />
      <div style={{ position: "relative", zIndex: 50 }}>
        <DashboardHeader lastUpdateSeconds={lastUpdateSeconds} sensorNodeOnline={connectionStatus} />
      </div>
      <div style={{ padding: "2rem", maxWidth: "1400px", margin: "0 auto", position: "relative", zIndex: 40 }}>

        {/* Hardware badge row */}
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "1rem" }}>
          <div style={{
            display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.4rem 1rem",
            borderRadius: 9999, backgroundColor: hwBadge.bg, border: `1px solid ${hwBadge.color}40`,
            color: hwBadge.color, fontSize: "0.85rem", fontWeight: 600,
          }}>
            {hwBadge.icon} {hwBadge.label}
          </div>
        </div>

        {/* Floating particle visualization */}
        <div style={{ marginBottom: "2.5rem", position: "relative" }}>
          <GlassSection style={{ padding: 0, overflow: "hidden" }}>
            <h3 style={{
              fontSize: "1.15rem", fontWeight: "bold", color: isDark ? "#FFFFFF" : "#1B3A20",
              textAlign: "center", padding: "1.2rem 0 0",
              letterSpacing: "0.06em", textTransform: "uppercase",
            }}>
              AI Workflow in Action
            </h3>
            <div style={{ position: "relative", width: "100%", height: "240px" }}>
              <canvas ref={canvasRef} style={{ display: "block", width: "100%", height: "100%" }} />
            </div>
          </GlassSection>

          {/* Live agents sidebar */}
          <div style={{ position: "absolute", top: "1rem", right: "1rem", width: 240, zIndex: 100 }}>
            <GlassSection style={{ padding: "1rem" }}>
              <h4 style={{ fontSize: "0.85rem", fontWeight: "bold", color: "#2ECC71", marginBottom: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Active Agents
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {["Supervisor", "Trend", "Output", "Ingress", "Health", "Alert", "Weather", "Response"].map((a) => (
                  <div key={a} style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                    <div style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: "#2ECC71", boxShadow: "0 0 6px #2ECC71" }} />
                    <span style={{ fontSize: "0.8rem", color: isDark ? "#E5E7EB" : "#1B3A20" }}>{a}</span>
                    <span style={{ fontSize: "0.65rem", color: isDark ? "#A7F3D0" : "#15803D", marginLeft: "auto" }}>Live</span>
                  </div>
                ))}
              </div>
            </GlassSection>
          </div>
        </div>

        {/* Control Buttons */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.5rem", marginBottom: "2rem" }}>
          <GlassSection style={{ padding: "2rem", textAlign: "center" }}>
            <CloudRain style={{ width: "2rem", height: "2rem", color: "#2563EB", margin: "0 auto 1rem" }} />
            <h3 style={{ fontSize: "1.125rem", fontWeight: "bold", color: isDark ? "#FFFFFF" : "#1B3A20", marginBottom: "1rem" }}>Rain Predictor</h3>
            <Button onClick={predictRain} disabled={loadingRain} style={{ width: "100%", backgroundColor: "#2ECC71", color: "white", padding: "0.75rem" }}>
              {loadingRain ? t('accel_sending') : t('accel_predict_rain')}
            </Button>
          </GlassSection>
          <GlassSection style={{ padding: "2rem", textAlign: "center" }}>
            <Leaf style={{ width: "2rem", height: "2rem", color: "#27AE60", margin: "0 auto 1rem" }} />
            <h3 style={{ fontSize: "1.125rem", fontWeight: "bold", color: isDark ? "#FFFFFF" : "#1B3A20", marginBottom: "1rem" }}>Crop Health</h3>
            <Button onClick={runSensorFusion} disabled={loadingFusion} style={{ width: "100%", backgroundColor: "#2ECC71", color: "white", padding: "0.75rem" }}>
              {loadingFusion ? t('accel_sending') : t('accel_health_check')}
            </Button>
          </GlassSection>
          <GlassSection style={{ padding: "2rem", textAlign: "center" }}>
            <Droplets style={{ width: "2rem", height: "2rem", color: "#8B5CF6", margin: "0 auto 1rem" }} />
            <h3 style={{ fontSize: "1.125rem", fontWeight: "bold", color: isDark ? "#FFFFFF" : "#1B3A20", marginBottom: "1rem" }}>Irrigation Model</h3>
            <Button onClick={runCombinedAnalysis} disabled={loadingCombined} style={{ width: "100%", backgroundColor: "#2ECC71", color: "white", padding: "0.75rem" }}>
              {loadingCombined ? t('accel_sending') : t('accel_run_analysis')}
            </Button>
          </GlassSection>
        </div>

        {/* ─── Rain Prediction Results ─── */}
        {rainPrediction && (
          <GlassSection style={{ marginBottom: "1.5rem", padding: "2rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
              <h3 style={{ fontSize: "1.25rem", fontWeight: "bold", color: isDark ? "#FFFFFF" : "#1B3A20" }}>️ Rain Prediction</h3>
              {modeBadge(rainPrediction.hardware_mode)}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
              <div style={{ padding: "1.5rem", borderRadius: "0.5rem", backgroundColor: getRiskColor(rainPrediction.prediction.rain_probability).bg }}>
                <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#374151", marginBottom: "0.5rem" }}>Rain Probability</p>
                <p style={{ fontSize: "2.25rem", fontWeight: "bold", color: getRiskColor(rainPrediction.prediction.rain_probability).text }}>
                  {rainPrediction.prediction.rain_probability}%
                </p>
              </div>
              <div style={{ padding: "1.5rem", backgroundColor: isDark ? "rgba(46,204,113,0.1)" : "rgba(46,204,113,0.05)", borderRadius: "0.5rem" }}>
                <p style={{ fontSize: "0.875rem", fontWeight: 600, color: isDark ? "#FFFFFF" : "#1B3A20", marginBottom: "0.5rem" }}>Recommendation</p>
                <p style={{ color: isDark ? "#FFFFFF" : "#1B3A20", fontSize: "0.95rem" }}>{rainPrediction.farmer_recommendation}</p>
              </div>
            </div>
            {rainPrediction.ai_insights && (
              <div style={{ marginTop: "1.5rem", padding: "1.5rem", backgroundColor: "rgba(99,102,241,0.1)", borderRadius: "0.5rem", borderLeft: "4px solid #6366F1" }}>
                <p style={{ fontSize: "0.95rem", fontWeight: 700, color: isDark ? "#A5B4FC" : "#4F46E5", marginBottom: "0.75rem" }}> LLM Analysis (Groq AI)</p>
                <p style={{ color: isDark ? "#E5E7EB" : "#374151", fontSize: "0.9rem", lineHeight: 1.7, whiteSpace: "pre-line" }}>{rainPrediction.ai_insights}</p>
              </div>
            )}
          </GlassSection>
        )}

        {/* ─── Crop Health Results ─── */}
        {sensorFusion && (
          <GlassSection style={{ marginBottom: "1.5rem", padding: "2rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
              <h3 style={{ fontSize: "1.25rem", fontWeight: "bold", color: isDark ? "#FFFFFF" : "#1B3A20" }}> Plant Health Check</h3>
              {modeBadge(sensorFusion.hardware_mode)}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1.5rem" }}>
              <div style={{ padding: "1.5rem", backgroundColor: isDark ? "rgba(46,204,113,0.1)" : "rgba(46,204,113,0.05)", borderRadius: "0.5rem" }}>
                <p style={{ fontSize: "0.85rem", color: isDark ? "#E5E7EB" : "#1B3A20", marginBottom: "0.5rem" }}>Plant Health Score</p>
                <p style={{ fontSize: "1.75rem", fontWeight: "bold", color: "#2ECC71" }}>{sensorFusion.fpga_result?.fusion_score ?? "N/A"}</p>
              </div>
              <div style={{ padding: "1.5rem", backgroundColor: isDark ? "rgba(249,115,22,0.1)" : "rgba(249,115,22,0.05)", borderRadius: "0.5rem" }}>
                <p style={{ fontSize: "0.85rem", color: isDark ? "#E5E7EB" : "#1B3A20", marginBottom: "0.5rem" }}>Stress Level</p>
                <p style={{ fontSize: "1.75rem", fontWeight: "bold", color: "#F97316" }}>{sensorFusion.fpga_result?.stress_index ?? "N/A"}%</p>
              </div>
              <div style={{ padding: "1.5rem", backgroundColor: isDark ? "rgba(59,130,246,0.1)" : "rgba(59,130,246,0.05)", borderRadius: "0.5rem" }}>
                <p style={{ fontSize: "0.85rem", color: isDark ? "#E5E7EB" : "#1B3A20", marginBottom: "0.5rem" }}>Alert Level</p>
                <p style={{ fontSize: "1.75rem", fontWeight: "bold", color: "#3B82F6" }}>{sensorFusion.fpga_result?.alert_level ?? "Normal"}</p>
              </div>
            </div>
            {sensorFusion.ai_insights && (
              <div style={{ marginTop: "1.5rem", padding: "1.5rem", backgroundColor: "rgba(99,102,241,0.1)", borderRadius: "0.5rem", borderLeft: "4px solid #6366F1" }}>
                <p style={{ fontSize: "0.95rem", fontWeight: 700, color: isDark ? "#A5B4FC" : "#4F46E5", marginBottom: "0.75rem" }}> LLM Analysis (Groq AI)</p>
                <p style={{ color: isDark ? "#E5E7EB" : "#374151", fontSize: "0.9rem", lineHeight: 1.7, whiteSpace: "pre-line" }}>{sensorFusion.ai_insights}</p>
              </div>
            )}
          </GlassSection>
        )}

        {/* ─── Irrigation Model Results ─── */}
        {combinedAnalysis && (
          <GlassSection style={{ padding: "2rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
              <h3 style={{ fontSize: "1.25rem", fontWeight: "bold", color: isDark ? "#FFFFFF" : "#1B3A20" }}>Irrigation Recommendation</h3>
              {modeBadge(combinedAnalysis.hardware_mode)}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1.5rem", marginBottom: "1.5rem" }}>
              <div style={{ padding: "1.5rem", backgroundColor: isDark ? "rgba(139,92,246,0.1)" : "rgba(139,92,246,0.05)", borderRadius: "0.5rem" }}>
                <p style={{ fontSize: "0.85rem", color: isDark ? "#E5E7EB" : "#1B3A20", marginBottom: "0.5rem" }}>Overall Risk</p>
                <p style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#8B5CF6" }}>{combinedAnalysis.combined_analysis?.overall_risk_level ?? "Low"}</p>
              </div>
              <div style={{ padding: "1.5rem", backgroundColor: isDark ? "rgba(46,204,113,0.1)" : "rgba(46,204,113,0.05)", borderRadius: "0.5rem" }}>
                <p style={{ fontSize: "0.85rem", color: isDark ? "#E5E7EB" : "#1B3A20", marginBottom: "0.5rem" }}>Plant Stress</p>
                <p style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#2ECC71" }}>{combinedAnalysis.combined_analysis?.stress_index ?? "N/A"}%</p>
              </div>
              <div style={{ padding: "1.5rem", backgroundColor: isDark ? "rgba(59,130,246,0.1)" : "rgba(59,130,246,0.05)", borderRadius: "0.5rem" }}>
                <p style={{ fontSize: "0.85rem", color: isDark ? "#E5E7EB" : "#1B3A20", marginBottom: "0.5rem" }}>Rain Chance</p>
                <p style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#3B82F6" }}>{combinedAnalysis.combined_analysis?.rain_probability ?? "N/A"}%</p>
              </div>
            </div>
            <div style={{ padding: "2rem", backgroundColor: isDark ? "rgba(46,204,113,0.15)" : "rgba(46,204,113,0.08)", borderRadius: "0.5rem", borderLeft: "4px solid #2ECC71" }}>
              <p style={{ fontSize: "1.1rem", fontWeight: 700, color: isDark ? "#E5E7EB" : "#1B3A20", marginBottom: "1rem" }}> What You Should Do Now:</p>
              <p style={{ color: isDark ? "#F3F4F6" : "#374151", fontSize: "1rem", lineHeight: 1.6 }}>{combinedAnalysis.combined_analysis?.recommendation}</p>
            </div>
            {combinedAnalysis.ai_enhancement && (
              <div style={{ marginTop: "1.5rem", padding: "1.5rem", backgroundColor: "rgba(99,102,241,0.1)", borderRadius: "0.5rem", borderLeft: "4px solid #6366F1" }}>
                <p style={{ fontSize: "0.95rem", fontWeight: 700, color: isDark ? "#A5B4FC" : "#4F46E5", marginBottom: "0.75rem" }}> LLM Deep Analysis (Groq AI)</p>
                <p style={{ color: isDark ? "#E5E7EB" : "#374151", fontSize: "0.9rem", lineHeight: 1.7, whiteSpace: "pre-line" }}>{combinedAnalysis.ai_enhancement}</p>
              </div>
            )}
          </GlassSection>
        )}
      </div>
    </div>
  );
}
