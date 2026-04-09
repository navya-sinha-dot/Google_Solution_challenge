import { useState, useEffect } from 'react';
import { useTheme } from 'next-themes';
import { useNavigate } from 'react-router-dom';
import { useVoiceAssistant } from '@/hooks/useVoiceAssistant';
import { useLanguage } from '@/contexts/LanguageContext';
import { getCurrentWeatherData, getSystemHealth, getRecentAlerts } from '@/lib/weatherData';
import { Mic, X, Volume2, Loader, AlertCircle, Sparkles } from 'lucide-react';
import { getGeminiResponse } from '@/lib/gemini';
import { cn } from '@/lib/utils';

export function VoiceAssistantButton() {
  const { isListening, isSpeaking, transcript, interimTranscript, error, isSupported, startListening, stopListening, speak, stopSpeaking, clearTranscript, parseCommand } = useVoiceAssistant();
  const { t } = useLanguage();
  const navigate = useNavigate();
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const [showModal, setShowModal] = useState(false);
  const [responses, setResponses] = useState<string[]>([]);
  const [micPermission, setMicPermission] = useState<'granted' | 'denied' | 'prompt' | null>(null);

  // Request microphone permission on mount
  useEffect(() => {
    const checkMicPermission = async () => {
      try {
        const permission = await navigator.permissions.query({ name: 'microphone' } as PermissionDescriptor);
        setMicPermission(permission.state as 'granted' | 'denied' | 'prompt');
        permission.addEventListener('change', () => {
          setMicPermission(permission.state as 'granted' | 'denied' | 'prompt');
        });
      } catch (err) {
        console.log('Microphone permission check not supported');
      }
    };
    checkMicPermission();
  }, []);

  // Handle voice commands
  useEffect(() => {
    if (transcript && !isListening) {
      handleVoiceCommand(transcript);
      clearTranscript();
    }
  }, [transcript, isListening, clearTranscript]);

  const handleVoiceCommand = async (text: string) => {
    try {
      // Send to backend /api/chat endpoint for generic AI response
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
      });

      const data = await response.json();
      const aiResponse = data.response || "I couldn't generate a response. Please try again.";
      const activeAgent = data.active_agent || "Supervisor Agent";

      // Format the response with agent identification
      const agentPrefix = `${activeAgent} says: `;
      const displayResponse = `[${activeAgent}] ${aiResponse}`;

      setResponses((prev) => [...prev, displayResponse]);
      speak(agentPrefix + aiResponse);
    } catch (err) {
      const fallback = 'Sorry, I could not process that request at this time.';
      setResponses((prev) => [...prev, `[Supervisor Agent] ${fallback}`]);
      speak('Supervisor Agent says: ' + fallback);
      console.error('Error handling voice command:', err);
    }
  };

  if (!isSupported) {
    return null;
  }

  const handleMicClick = async () => {
    if (micPermission !== 'granted') {
      // Request permission
      try {
        await navigator.mediaDevices.getUserMedia({ audio: true });
        setMicPermission('granted');
        setShowModal(true);
        startListening();
      } catch (err) {
        setMicPermission('denied');
        alert('Microphone permission denied. Please enable it in your browser settings.');
      }
    } else {
      setShowModal(true);
      if (!isListening && !isSpeaking) {
        // Pre-warm the speech synthesis within user interaction
        window.speechSynthesis.speak(new SpeechSynthesisUtterance(""));
        startListening();
      }
    }
  };

  return (
    <>
      {/* Floating Voice Button with Permission Alert */}
      <div className="fixed bottom-6 right-6 z-40 flex flex-col items-end gap-3">
        {micPermission === 'denied' && (
          <div className="bg-yellow-100 border border-yellow-400 text-yellow-800 px-4 py-2 rounded-lg text-xs max-w-xs shadow-lg">
             Microphone blocked. Enable it in browser settings to use voice commands.
          </div>
        )}
        {!isSupported && (
          <div className="bg-red-100 border border-red-400 text-red-800 px-4 py-2 rounded-lg text-xs max-w-xs shadow-lg">
            Voice assistant not supported in your browser
          </div>
        )}
        <button
          onClick={handleMicClick}
          style={{
            width: '56px', height: '56px', borderRadius: '50%',
            background: isDark ? '#2A2A2A' : '#FFFFFF',
            boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
            border: isDark ? '1px solid rgba(255,255,255,0.1)' : '1px solid rgba(0,0,0,0.05)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.3s ease',
            color: isDark ? '#FFF' : '#000',
          }}
          className={isListening ? 'scale-110 animate-pulse' : ''}
          title="Voice Assistant - Click to speak"
        >
          {isListening ? (
            <Loader style={{ width: 24, height: 24, animation: 'spin 1s linear infinite' }} />
          ) : isSpeaking ? (
            <Volume2 style={{ width: 24, height: 24, animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' }} />
          ) : (
            <Mic style={{ width: 24, height: 24 }} />
          )}
        </button>
      </div>

      {/* Voice Assistant Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card rounded-2xl shadow-2xl w-full max-w-md border border-border">
            {/* Header with primary color */}
            <div className="bg-gradient-to-r from-primary to-primary/80 text-primary-foreground p-6 flex items-center justify-between rounded-t-2xl">
              <div className="flex items-center gap-3">
                <div className="bg-background/20 p-2 rounded-lg">
                  <Sparkles className="w-6 h-6 text-yellow-300" />
                </div>
                <div>
                  <h2 className="text-xl font-bold">{t('voice_title')}</h2>
                  <p className="text-primary-foreground/80 text-xs">{t('voice_subtitle')}</p>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowModal(false);
                  stopListening();
                  stopSpeaking();
                  clearTranscript();
                  setResponses([]);
                }}
                className="p-2 hover:bg-background/20 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-4 max-h-96 overflow-y-auto bg-gradient-to-b from-primary/5 to-background">
              {/* Error Display */}
              {error && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-destructive">{error}</p>
                </div>
              )}

              {/* Status */}
              <div className="text-center">
                {isListening && (
                  <div className="space-y-3">
                    <div className="flex justify-center gap-2">
                      <div className="w-3 h-3 bg-primary rounded-full animate-pulse"></div>
                      <div className="w-3 h-3 bg-primary/60 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                      <div className="w-3 h-3 bg-primary/30 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                    </div>
                    <p className="text-sm font-medium text-primary">{t('voice_listening')}</p>
                  </div>
                )}

                {isSpeaking && (
                  <div className="space-y-3">
                    <div className="flex justify-center gap-1">
                      {[0, 1, 2].map((i) => (
                        <div
                          key={i}
                          className="w-2 h-10 bg-primary rounded-full animate-pulse"
                          style={{ animationDelay: `${i * 150}ms` }}
                        ></div>
                      ))}
                    </div>
                    <p className="text-sm font-bold text-primary animate-pulse"> SkyView is speaking...</p>
                  </div>
                )}

                {!isListening && !isSpeaking && transcript && (
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-success/20 flex items-center justify-center">
                      <Loader className="w-5 h-5 text-success animate-spin" />
                    </div>
                    <p className="text-sm font-medium text-success">Processing atmospheric query...</p>
                  </div>
                )}
              </div>

              {/* Transcript */}
              {(transcript || interimTranscript) && (
                <div className="bg-muted rounded-lg p-4 border border-border">
                  <p className="text-xs font-semibold text-muted-foreground mb-2"> Your Command:</p>
                  <p className={cn("text-sm font-medium", interimTranscript ? "text-foreground/50 italic" : "text-foreground")}>
                    {transcript || interimTranscript}
                  </p>
                </div>
              )}

              {/* Responses */}
              {responses.length > 0 && (
                <div className="space-y-3">
                  <p className="text-xs font-semibold text-muted-foreground flex items-center justify-between">
                    <span> Assistant:</span>
                    <span className="text-[10px] opacity-50 font-normal italic">Click bubble to hear again</span>
                  </p>
                  <div className="space-y-3 max-h-48 overflow-y-auto pr-2 scrollbar-thin">
                    {responses.map((response, idx) => (
                      <div
                        key={idx}
                        onClick={() => speak(response)}
                        className="bg-primary/5 hover:bg-primary/10 transition-colors cursor-pointer rounded-xl p-4 border border-primary/10 group relative"
                      >
                        <p className="text-sm text-foreground leading-relaxed">{response}</p>
                        <Volume2 className="absolute top-2 right-2 w-3 h-3 text-primary opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Commands Help */}
              {!transcript && responses.length === 0 && (
                <div className="bg-muted rounded-lg p-4 border border-border">
                  <p className="text-xs font-semibold text-muted-foreground mb-3"> Ask anything:</p>
                  <ul className="text-xs text-muted-foreground space-y-1.5 font-medium">
                    <li>• "What's the current weather?"</li>
                    <li>• "What are today's mandi rates for wheat?"</li>
                    <li>• "What's the best price for tomato right now?"</li>
                    <li>• "Should I sell my onions today or wait?"</li>
                    <li>• "How is my soil moisture?"</li>
                    <li>• "Tell me about cotton market prices"</li>
                    <li>• Or any other question!</li>
                  </ul>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="bg-muted border-t border-border p-6 flex flex-col gap-3 rounded-b-2xl">
              {isListening ? (
                <div className="flex items-center justify-center gap-3 text-primary animate-pulse">
                  <span className="relative flex h-3 w-3">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-primary"></span>
                  </span>
                  <p className="text-sm font-bold uppercase tracking-widest">Listening – Just stop talking to send</p>
                </div>
              ) : isSpeaking ? (
                <button
                  onClick={() => stopSpeaking()}
                  className="w-full px-4 py-3 bg-destructive/10 hover:bg-destructive/20 text-destructive rounded-xl font-bold transition-all flex items-center justify-center gap-2"
                >
                  <X className="w-4 h-4" />
                  Interrupt Assistant
                </button>
              ) : (
                <button
                  onClick={() => startListening()}
                  className="w-full px-4 py-4 bg-primary hover:bg-primary/90 text-primary-foreground rounded-xl font-black text-lg shadow-xl shadow-primary/20 transition-all flex items-center justify-center gap-3 group"
                >
                  <Mic className="w-6 h-6 group-hover:scale-110 transition-transform" />
                  {t('voice_start')}
                </button>
              )}
            </div>

          </div>
        </div>
      )}
    </>
  );
}
