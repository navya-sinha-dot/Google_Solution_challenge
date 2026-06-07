import { useState, useEffect, useRef } from 'react';
import { useTheme } from 'next-themes';
import { useNavigate } from 'react-router-dom';
import { useVoiceAssistant } from '@/hooks/useVoiceAssistant';
import { useLanguage } from '@/contexts/LanguageContext';
import { Mic, X, Square, RotateCcw, AlignLeft } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || '';
const PRIMARY = '#10B981';

export function VoiceAssistantButton() {
  const {
    isListening, isSpeaking, transcript, interimTranscript,
    error, isSupported, startListening, stopListening,
    speak, stopSpeaking, clearTranscript,
  } = useVoiceAssistant();
  const { t } = useLanguage();
  const navigate = useNavigate();
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const [showLive, setShowLive] = useState(false);
  const [micPermission, setMicPermission] = useState<'granted' | 'denied' | 'prompt' | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastResponse, setLastResponse] = useState<string | null>(null);
  const [userText, setUserText] = useState<string | null>(null);
  const [thinkingSteps, setThinkingSteps] = useState<string[]>([]);
  const thinkingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const THINKING_LINES = [
    'आपका सवाल पढ़ रहा हूँ',
    'Scanning for missing details that affect accuracy',
    'भाषा और इरादा समझ रहा हूँ',
    'संदर्भ जाँच रहा हूँ',
    'Reading your message carefully',
    'Current phase: Analyzing your voice request',
    'Preparing final response handoff',
  ];

  useEffect(() => {
    navigator.permissions?.query({ name: 'microphone' } as PermissionDescriptor)
      .then(p => {
        setMicPermission(p.state as any);
        p.addEventListener('change', () => setMicPermission(p.state as any));
      }).catch(() => {});
  }, []);

  useEffect(() => {
    if (transcript && !isListening) {
      setUserText(transcript);
      handleVoiceCommand(transcript);
      clearTranscript();
    }
  }, [transcript, isListening]);

  useEffect(() => {
    if (isProcessing) {
      let i = 0;
      setThinkingSteps([THINKING_LINES[0]]);
      thinkingRef.current = setInterval(() => {
        i++;
        if (i < THINKING_LINES.length) {
          setThinkingSteps(prev => [...prev, THINKING_LINES[i]]);
        } else {
          clearInterval(thinkingRef.current!);
        }
      }, 800);
    } else {
      if (thinkingRef.current) clearInterval(thinkingRef.current);
      setThinkingSteps([]);
    }
    return () => { if (thinkingRef.current) clearInterval(thinkingRef.current); };
  }, [isProcessing]);

  const handleVoiceCommand = async (text: string) => {
    setIsProcessing(true);
    setLastResponse(null);
    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      const aiResponse = data.response || "I couldn't generate a response. Please try again.";
      setLastResponse(aiResponse);
      speak(aiResponse);
    } catch {
      const fallback = 'Sorry, I could not process that request at this time.';
      setLastResponse(fallback);
      speak(fallback);
    } finally {
      setIsProcessing(false);
    }
  };

  if (!isSupported) return null;

  const handleMicClick = async () => {
    if (micPermission !== 'granted') {
      try {
        await navigator.mediaDevices.getUserMedia({ audio: true });
        setMicPermission('granted');
        openLive();
      } catch {
        setMicPermission('denied');
        alert('Microphone permission denied. Please enable it in your browser settings.');
      }
    } else {
      openLive();
    }
  };

  const openLive = () => {
    setShowLive(true);
    setLastResponse(null);
    setUserText(null);
    window.speechSynthesis?.speak(new SpeechSynthesisUtterance(''));
    startListening();
  };

  const closeLive = () => {
    setShowLive(false);
    stopListening();
    stopSpeaking();
    clearTranscript();
    setLastResponse(null);
    setUserText(null);
    setIsProcessing(false);
  };

  const handleRestart = () => {
    stopSpeaking();
    setLastResponse(null);
    setUserText(null);
    setIsProcessing(false);
    startListening();
  };

  // Status label for center
  const statusLabel = (() => {
    if (isListening) return null; // shown differently
    if (isProcessing) return 'Thinking...';
    if (isSpeaking) return 'Speaking...';
    if (lastResponse) return null;
    return null;
  })();

  return (
    <>
      {/* Floating trigger */}
      <div className="fixed bottom-6 right-6 z-40">
        {micPermission === 'denied' && (
          <div className="mb-2 bg-yellow-100 border border-yellow-400 text-yellow-800 px-3 py-2 rounded-lg text-xs max-w-xs shadow-lg">
            Microphone blocked. Enable it in browser settings.
          </div>
        )}
        <button
          onClick={handleMicClick}
          style={{
            width: '52px', height: '52px', borderRadius: '50%',
            background: isDark ? 'rgba(30,30,30,0.9)' : '#fff',
            boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
            border: `1.5px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.07)'}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer',
            transition: 'transform 0.2s, box-shadow 0.2s',
            color: isDark ? '#fff' : '#000',
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(1.08)'; }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(1)'; }}
        >
          <Mic style={{ width: 22, height: 22 }} />
        </button>
      </div>

      {/* Live overlay — exactly matches the screenshot */}
      {showLive && (
        <div style={{
          position: 'fixed',
          inset: 0,
          zIndex: 100,
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'center',
          background: 'rgba(0,0,0,0.3)',
          backdropFilter: 'blur(4px)',
        }}>
          {/* Sheet panel */}
          <div style={{
            width: '100%',
            maxWidth: '420px',
            background: isDark ? '#0f1f15' : '#e8f5ee',
            borderRadius: '28px 28px 0 0',
            minHeight: '70vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            animation: 'slideUp 0.3s cubic-bezier(.32,1,.56,1)',
          }}>

            {/* Top bar */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '18px 20px 12px',
            }}>
              <button
                onClick={closeLive}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.4)' }}
              >
                <X size={20} />
              </button>

              <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                <div style={{
                  width: '8px', height: '8px', borderRadius: '50%',
                  background: isListening || isProcessing || isSpeaking ? PRIMARY : 'rgba(0,0,0,0.2)',
                  boxShadow: isListening ? `0 0 8px ${PRIMARY}` : 'none',
                  animation: isListening ? 'livePulse 1.4s ease-in-out infinite' : 'none',
                }} />
                <span style={{
                  fontSize: '15px', fontWeight: 600,
                  color: isDark ? '#fff' : '#111',
                  letterSpacing: '-0.2px',
                }}>
                  Live
                </span>
              </div>

              <button
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.4)' }}
              >
                <AlignLeft size={18} />
              </button>
            </div>

            {/* User transcript */}
            {(userText || interimTranscript) && (
              <div style={{ padding: '4px 20px 0' }}>
                <p style={{
                  margin: 0,
                  fontSize: '14px',
                  color: isDark ? 'rgba(255,255,255,0.8)' : 'rgba(0,0,0,0.75)',
                  fontWeight: 500,
                  lineHeight: 1.5,
                }}>
                  {userText || interimTranscript}
                </p>
              </div>
            )}

            {/* Center area */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '24px 20px' }}>
              {isListening && !userText && (
                <div style={{ textAlign: 'center' }}>
                  {/* Waveform dots */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px', marginBottom: '20px', height: '36px' }}>
                    {[0.6, 0.9, 1, 0.7, 0.5, 0.8, 1, 0.6, 0.4, 0.7, 0.95, 0.6].map((h, i) => (
                      <div key={i} style={{
                        width: '3px',
                        height: `${h * 28}px`,
                        borderRadius: '2px',
                        background: PRIMARY,
                        opacity: 0.7,
                        animation: `wave 1.2s ease-in-out ${i * 80}ms infinite alternate`,
                      }} />
                    ))}
                  </div>
                  <p style={{ fontSize: '17px', fontWeight: 600, color: isDark ? '#fff' : '#111', margin: 0 }}>Tap mic to speak</p>
                  <p style={{ fontSize: '12px', color: isDark ? 'rgba(255,255,255,0.4)' : 'rgba(0,0,0,0.4)', margin: '6px 0 0', fontWeight: 400 }}>
                    Tap response to expand. Long press for full view.
                  </p>
                </div>
              )}

              {isProcessing && (
                <div style={{ textAlign: 'center', width: '100%' }}>
                  <p style={{ fontSize: '22px', fontWeight: 600, color: isDark ? '#fff' : '#111', margin: '0 0 6px' }}>Thinking...</p>
                  <p style={{ fontSize: '12px', color: isDark ? 'rgba(255,255,255,0.4)' : 'rgba(0,0,0,0.4)', margin: '0 0 20px', fontWeight: 400 }}>
                    Tap response to expand. Long press for full view.
                  </p>
                </div>
              )}

              {lastResponse && !isProcessing && (
                <div
                  onClick={() => speak(lastResponse)}
                  style={{
                    width: '100%',
                    background: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.7)',
                    borderRadius: '16px',
                    padding: '16px',
                    cursor: 'pointer',
                    border: isDark ? '1px solid rgba(255,255,255,0.08)' : '1px solid rgba(0,0,0,0.06)',
                  }}
                >
                  <p style={{
                    margin: 0,
                    fontSize: '14px',
                    color: isDark ? 'rgba(255,255,255,0.85)' : 'rgba(0,0,0,0.8)',
                    lineHeight: 1.55,
                    fontWeight: 400,
                  }}>
                    {lastResponse}
                  </p>
                </div>
              )}

              {!isListening && !isProcessing && !lastResponse && !userText && (
                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: '17px', fontWeight: 600, color: isDark ? '#fff' : '#111', margin: 0 }}>Tap mic to speak</p>
                  <p style={{ fontSize: '12px', color: isDark ? 'rgba(255,255,255,0.4)' : 'rgba(0,0,0,0.4)', margin: '6px 0 0' }}>
                    Tap response to expand. Long press for full view.
                  </p>
                </div>
              )}
            </div>

            {/* Thinking panel */}
            {isProcessing && thinkingSteps.length > 0 && (
              <div style={{
                margin: '0 14px 10px',
                background: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(255,255,255,0.6)',
                borderRadius: '14px',
                padding: '12px 14px',
                border: isDark ? '1px solid rgba(255,255,255,0.07)' : '1px solid rgba(0,0,0,0.06)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <span style={{ fontSize: '11px', fontWeight: 700, color: PRIMARY }}>✦ Thinking</span>
                  </div>
                  <span style={{ fontSize: '10px', color: isDark ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.3)' }}>
                    {thinkingSteps.length}s ⌃
                  </span>
                </div>
                {thinkingSteps.map((step, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', marginBottom: '3px' }}>
                    <span style={{ color: PRIMARY, fontSize: '10px', marginTop: '2px', flexShrink: 0 }}>•</span>
                    <span style={{
                      fontSize: '11.5px',
                      color: i === thinkingSteps.length - 1
                        ? (isDark ? '#fff' : '#111')
                        : (isDark ? 'rgba(255,255,255,0.45)' : 'rgba(0,0,0,0.45)'),
                      fontWeight: i === thinkingSteps.length - 1 ? 500 : 400,
                    }}>
                      {step}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Bottom status bar */}
            {isListening && (
              <div style={{
                margin: '0 14px 12px',
                background: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(255,255,255,0.55)',
                borderRadius: '20px',
                padding: '10px 16px',
                border: isDark ? '1px solid rgba(255,255,255,0.06)' : '1px solid rgba(0,0,0,0.05)',
              }}>
                <p style={{ margin: 0, fontSize: '12px', color: isDark ? 'rgba(255,255,255,0.45)' : 'rgba(0,0,0,0.45)', fontWeight: 400 }}>
                  Tap mic to speak
                </p>
              </div>
            )}

            {/* Action bar */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 28px 28px',
              gap: '16px',
            }}>
              {/* Transcript toggle */}
              <button
                style={{
                  width: '44px', height: '44px', borderRadius: '50%',
                  background: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.07)',
                  border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: isDark ? 'rgba(255,255,255,0.6)' : 'rgba(0,0,0,0.5)',
                }}
              >
                <AlignLeft size={18} />
              </button>

              {/* Restart */}
              <button
                onClick={handleRestart}
                style={{
                  width: '44px', height: '44px', borderRadius: '50%',
                  background: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.07)',
                  border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: isDark ? 'rgba(255,255,255,0.6)' : 'rgba(0,0,0,0.5)',
                }}
              >
                <RotateCcw size={18} />
              </button>

              {/* Main mic / stop button */}
              {isListening || isProcessing ? (
                <button
                  onClick={isListening ? stopListening : undefined}
                  style={{
                    width: '60px', height: '60px', borderRadius: '50%',
                    background: isListening ? PRIMARY : 'rgba(16,185,129,0.2)',
                    border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    boxShadow: isListening ? `0 4px 20px rgba(16,185,129,0.4)` : 'none',
                    color: '#fff',
                    animation: isProcessing ? 'none' : undefined,
                  }}
                >
                  {isProcessing ? (
                    <div style={{
                      width: '20px', height: '20px', borderRadius: '50%',
                      background: '#fff',
                      animation: 'processingPulse 1s ease-in-out infinite',
                    }} />
                  ) : (
                    <Mic size={24} />
                  )}
                </button>
              ) : (
                <button
                  onClick={() => startListening()}
                  style={{
                    width: '60px', height: '60px', borderRadius: '50%',
                    background: PRIMARY,
                    border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    boxShadow: `0 4px 20px rgba(16,185,129,0.35)`,
                    color: '#fff',
                  }}
                >
                  <Mic size={24} />
                </button>
              )}

              {/* Stop / close */}
              <button
                onClick={isSpeaking ? stopSpeaking : closeLive}
                style={{
                  width: '44px', height: '44px', borderRadius: '50%',
                  background: '#EF4444',
                  border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#fff',
                }}
              >
                <X size={18} />
              </button>

              {/* Expand */}
              <button
                style={{
                  width: '44px', height: '44px', borderRadius: '50%',
                  background: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.07)',
                  border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: isDark ? 'rgba(255,255,255,0.6)' : 'rgba(0,0,0,0.5)',
                }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="15 3 21 3 21 9" /><polyline points="9 21 3 21 3 15" />
                  <line x1="21" y1="3" x2="14" y2="10" /><line x1="3" y1="21" x2="10" y2="14" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Animations */}
      <style>{`
        @keyframes slideUp {
          from { transform: translateY(100%); opacity: 0; }
          to   { transform: translateY(0);    opacity: 1; }
        }
        @keyframes livePulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
        @keyframes wave {
          from { transform: scaleY(0.4); }
          to   { transform: scaleY(1); }
        }
        @keyframes processingPulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(0.7); opacity: 0.6; }
        }
      `}</style>
    </>
  );
}