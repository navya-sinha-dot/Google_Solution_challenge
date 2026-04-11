import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from 'next-themes';
import { FarmBackground } from '@/components/FarmTheme';
import {
  Cpu, Wifi, Thermometer, Droplets, Wind, Sun,
  Sprout, Zap, Shield, ArrowLeft, CheckCircle2, ShoppingCart,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useState } from 'react';

const DEVICE_ID = 'AGRISENSE-WS01';

const SPECS = [
  { icon: Thermometer, label: 'Temperature', detail: '±0.1°C accuracy', color: '#E53935' },
  { icon: Droplets, label: 'Humidity', detail: '0–100% RH', color: '#2196F3' },
  { icon: Sprout, label: 'Soil Moisture', detail: 'Capacitive sensor', color: '#4CAF50' },
  { icon: Wind, label: 'Wind Speed', detail: 'Anemometer, 0–60 km/h', color: '#00BCD4' },
  { icon: Sun, label: 'Light & UV', detail: 'Full-spectrum sensor', color: '#FF9800' },
  { icon: Cpu, label: 'FPGA Core', detail: 'Xilinx ZC706', color: '#9C27B0' },
  { icon: Wifi, label: 'Connectivity', detail: 'MQTT over Wi-Fi', color: '#2ECC71' },
  { icon: Zap, label: 'AI Inference', detail: 'On-device edge AI', color: '#F59E0B' },
];

const FEATURES = [
  'Real-time streaming to your dashboard',
  'FPGA-accelerated rain prediction & crop health analysis',
  'Automated alerts for critical farm conditions',
  'LangGraph multi-agent AI analysis',
  'Works with any Indian market for crop pricing',
  'Voice assistant integration',
];

export default function BuyHardware() {
  const { connectHardware } = useAuth();
  const navigate = useNavigate();
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const [ordered, setOrdered] = useState(false);
  const [connecting, setConnecting] = useState(false);

  const textPrimary = isDark ? '#A8D89A' : '#1B3A20';
  const textSecondary = isDark ? '#6A8A6A' : '#5A7A60';
  const cardBg = isDark ? 'rgba(15, 25, 15, 0.82)' : 'rgba(255, 255, 255, 0.92)';

  const handleDemoConnect = async () => {
    setConnecting(true);
    await new Promise(r => setTimeout(r, 1500));
    connectHardware(DEVICE_ID);
    navigate('/dashboard');
  };

  return (
    <div style={{ position: 'relative', minHeight: '100vh', overflow: 'hidden' }}>
      <FarmBackground />

      <div style={{ position: 'relative', zIndex: 10, maxWidth: '1000px', margin: '0 auto', padding: '40px 24px 80px' }}>

        {/* Back button */}
        <button
          onClick={() => navigate('/hardware-setup')}
          style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            background: 'none', border: 'none', cursor: 'pointer',
            color: textSecondary, fontSize: '14px', fontWeight: 600,
            marginBottom: '32px', padding: 0,
          }}
        >
          <ArrowLeft style={{ width: '16px', height: '16px' }} />
          Back to Hardware Setup
        </button>

        {/* Hero */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          style={{
            background: cardBg,
            backdropFilter: 'blur(18px)',
            WebkitBackdropFilter: 'blur(18px)',
            borderRadius: '24px',
            padding: '48px 40px',
            marginBottom: '24px',
            border: isDark ? '1px solid rgba(46,204,113,0.15)' : '1px solid rgba(200,230,200,0.5)',
            boxShadow: isDark ? '0 12px 40px rgba(0,0,0,0.3)' : '0 12px 40px rgba(0,0,0,0.08)',
          }}
        >
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '48px', alignItems: 'center' }}>
            {/* Left: info */}
            <div>
              <div style={{
                display: 'inline-flex', alignItems: 'center', gap: '8px',
                background: 'rgba(46,204,113,0.1)', borderRadius: '20px',
                padding: '6px 14px', marginBottom: '20px',
                border: '1px solid rgba(46,204,113,0.2)',
              }}>
                <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#2ECC71' }} />
                <span style={{ fontSize: '11px', fontWeight: 800, color: '#2ECC71', textTransform: 'uppercase', letterSpacing: '1px' }}>
                  New Generation
                </span>
              </div>

              <h1 style={{
                fontSize: '36px', fontWeight: 900, color: textPrimary,
                fontFamily: "'Nunito', sans-serif", lineHeight: 1.2, marginBottom: '16px',
              }}>
                AgriSense WS01
              </h1>
              <p style={{ fontSize: '15px', color: textSecondary, lineHeight: 1.7, marginBottom: '28px' }}>
                The world's first FPGA-accelerated precision weather station built for Indian farmers.
                Streams 8 sensor channels in real-time, runs AI inference on-device, and connects
                directly to your SkyView AI dashboard.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '32px' }}>
                {FEATURES.map((f, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                    <CheckCircle2 style={{ width: '16px', height: '16px', color: '#2ECC71', flexShrink: 0, marginTop: '2px' }} />
                    <span style={{ fontSize: '13px', color: textSecondary }}>{f}</span>
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                {!ordered ? (
                  <button
                    onClick={() => setOrdered(true)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '8px',
                      padding: '14px 28px', borderRadius: '14px', border: 'none',
                      background: 'linear-gradient(135deg, #2ECC71, #1a9e52)',
                      color: 'white', fontSize: '15px', fontWeight: 800,
                      cursor: 'pointer',
                      boxShadow: '0 4px 16px rgba(46,204,113,0.4)',
                    }}
                  >
                    <ShoppingCart style={{ width: '18px', height: '18px' }} />
                    Order Now — ₹12,999
                  </button>
                ) : (
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    padding: '14px 24px', borderRadius: '14px',
                    background: 'rgba(46,204,113,0.1)',
                    border: '2px solid #2ECC71',
                    color: '#2ECC71', fontSize: '14px', fontWeight: 800,
                  }}>
                    <CheckCircle2 style={{ width: '18px', height: '18px' }} />
                    Order Placed! Delivery in 3–5 days
                  </div>
                )}

                <button
                  onClick={handleDemoConnect}
                  disabled={connecting}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '8px',
                    padding: '14px 24px', borderRadius: '14px',
                    border: isDark ? '1px solid rgba(33,150,243,0.3)' : '1px solid rgba(33,150,243,0.3)',
                    background: isDark ? 'rgba(33,150,243,0.1)' : 'rgba(33,150,243,0.06)',
                    color: '#2196F3', fontSize: '14px', fontWeight: 800,
                    cursor: connecting ? 'wait' : 'pointer',
                  }}
                >
                  <Wifi style={{ width: '16px', height: '16px' }} />
                  {connecting ? 'Connecting...' : 'Try Demo (Connect WS01)'}
                </button>
              </div>
            </div>

            {/* Right: visual device card */}
            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <div style={{
                width: '280px', height: '320px', borderRadius: '24px',
                background: isDark
                  ? 'linear-gradient(145deg, rgba(46,204,113,0.12), rgba(33,150,243,0.08))'
                  : 'linear-gradient(145deg, rgba(46,204,113,0.08), rgba(33,150,243,0.05))',
                border: isDark ? '1px solid rgba(46,204,113,0.2)' : '1px solid rgba(46,204,113,0.15)',
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                justifyContent: 'center', gap: '16px',
                boxShadow: '0 20px 60px rgba(0,0,0,0.1)',
                position: 'relative', overflow: 'hidden',
              }}>
                {/* Glow */}
                <div style={{
                  position: 'absolute', top: '30%', left: '50%',
                  transform: 'translate(-50%, -50%)',
                  width: '140px', height: '140px', borderRadius: '50%',
                  background: 'radial-gradient(circle, rgba(46,204,113,0.15), transparent 70%)',
                }} />

                <div style={{
                  width: '80px', height: '80px', borderRadius: '22px',
                  background: 'linear-gradient(135deg, #2ECC71, #1a9e52)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  boxShadow: '0 8px 24px rgba(46,204,113,0.4)',
                }}>
                  <Cpu style={{ width: '40px', height: '40px', color: 'white' }} />
                </div>

                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: '18px', fontWeight: 900, color: textPrimary, margin: 0 }}>AgriSense WS01</p>
                  <p style={{ fontSize: '12px', color: '#2ECC71', fontWeight: 700, margin: '4px 0 0' }}>FPGA Weather Station</p>
                </div>

                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center', padding: '0 16px' }}>
                  {['MQTT', 'IoT', 'FPGA', 'AI'].map(t => (
                    <span key={t} style={{
                      fontSize: '10px', fontWeight: 800,
                      padding: '3px 9px', borderRadius: '20px',
                      background: 'rgba(46,204,113,0.12)',
                      color: '#2ECC71', border: '1px solid rgba(46,204,113,0.2)',
                    }}>{t}</span>
                  ))}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Shield style={{ width: '13px', height: '13px', color: textSecondary }} />
                  <span style={{ fontSize: '11px', color: textSecondary, fontWeight: 600 }}>1-Year Warranty</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Specs grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
        >
          <h2 style={{ fontSize: '18px', fontWeight: 800, color: textPrimary, marginBottom: '16px', fontFamily: "'Nunito', sans-serif" }}>
            Sensor Specifications
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
            {SPECS.map(({ icon: Icon, label, detail, color }) => (
              <div key={label} style={{
                background: cardBg,
                backdropFilter: 'blur(12px)',
                WebkitBackdropFilter: 'blur(12px)',
                borderRadius: '16px',
                padding: '18px 20px',
                border: isDark ? '1px solid rgba(255,255,255,0.04)' : '1px solid rgba(200,230,200,0.4)',
                display: 'flex', alignItems: 'center', gap: '14px',
              }}>
                <div style={{
                  width: '40px', height: '40px', borderRadius: '12px',
                  background: `${color}15`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  <Icon style={{ width: '20px', height: '20px', color }} />
                </div>
                <div>
                  <p style={{ fontSize: '13px', fontWeight: 800, color: textPrimary, margin: 0 }}>{label}</p>
                  <p style={{ fontSize: '11px', color: textSecondary, margin: 0 }}>{detail}</p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
