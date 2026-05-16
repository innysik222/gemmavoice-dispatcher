"use client";

import { useState, useEffect } from 'react';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import { useCamera } from '../hooks/useCamera';

/**
 * GEMMAVOICE v1.1 [HACKATHON BUILD]
 * Mobile-First Emergency Dispatcher with Vision.
 * Designed for field use in disaster zones.
 */

const DEMO_SCENARIOS = [
  {
    type: "Victim Registration",
    user_text: "Register a new victim. Male, roughly 40 years old, found near the collapsed stairwell.",
    response: "Victim registered. Assigned ID: V-402. Male, ~40yo, location: collapsed stairwell. Initializing triage protocol.",
    new_alert: {title: "NEW VICTIM", msg: "V-402 registered at collapsed stairwell.", style: "safe"}
  },
  {
    type: "Triage",
    user_text: "Victim V-402 has severe lacerations on the right arm and a capillary refill of 4 seconds.",
    response: "WARNING. Capillary refill > 2 seconds indicates compromised perfusion. Triage category is IMMEDIATE (RED). Apply tourniquet and prepare for rapid evacuation.",
    new_alert: {title: "TRIAGE UPDATE", msg: "V-402 categorized as IMMEDIATE (RED).", style: "alert"}
  },
  {
    type: "Mesh Alert",
    user_text: "Broadcast an evacuation request for V-402 over the LoRa mesh network.",
    response: "Evacuation request broadcasted via LoRa mesh. Priority 1 medical evac requested for V-402. Awaiting ACK from command center.",
    new_alert: {title: "MESH TX", msg: "Evac request sent via LoRa.", style: "safe"}
  },
  {
    type: "Inventory",
    user_text: "What is our current stock of tourniquets and morphine?",
    response: "Current inventory: 12 CAT Tourniquets, 4 vials of Morphine (10mg/mL). Warning: Morphine stock is critically low.",
    inventory: [
      {name: "CAT Tourniquet", qty: 12},
      {name: "Morphine 10mg", qty: 4},
      {name: "QuikClot", qty: 8},
      {name: "Saline 500ml", qty: 15}
    ]
  },
  {
    type: "Victim Search",
    user_text: "Have we seen a female child wearing a blue jacket?",
    response: "Checking logs... Yes. Victim V-398 matches that description. Registered 45 minutes ago in the minor treatment sector."
  },
  {
    type: "Protocol Lookup",
    user_text: "Pull up the WHO START protocol for pediatric patients.",
    response: "WHO JumpSTART Pediatric Protocol: 1. If breathing > 45 or < 15, tag IMMEDIATE. 2. If no palpable pulse, tag IMMEDIATE. 3. If inappropriate posturing, tag IMMEDIATE. Please verify vitals."
  }
];

export default function mobileDashboard() {
  const [lastResponse, setLastResponse] = useState<string>("");
  const [lastTranscription, setLastTranscription] = useState<string>("");
  const [status, setStatus] = useState<string>("OFFLINE");
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [inputText, setInputText] = useState<string>("");
  const [isQuietMode, setIsQuietMode] = useState(false);
  const [stagedImage, setStagedImage] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<any[]>([{title: "FIELD BOOT", msg: "Awaiting local telemetry.", style: "safe"}]);
  const [inventory, setInventory] = useState<any[]>([]);
  const [hasMounted, setHasMounted] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [demoIndex, setDemoIndex] = useState(0);
  const [isDemoMicActive, setIsDemoMicActive] = useState(false);
  
  const { isRecording: isRealMicActive, startRecording, stopRecording } = useAudioRecorder(ws);
  const isMicActive = isDemoMode ? isDemoMicActive : isRealMicActive;
  const { videoRef, canvasRef, startCamera, stopCamera, captureFrame, isActive: iCameraActive } = useCamera();

  // TTS Helper
  const speakResponse = (text: string) => {
    if (!('speechSynthesis' in window)) return;
    
    window.speechSynthesis.cancel();
    
    // Split text into smaller chunks to prevent Chrome TTS from timing out on long responses
    const chunks = text.match(/[^.!?]+[.!?]+/g) || [text];
    
    chunks.forEach((chunk, index) => {
        const utterance = new SpeechSynthesisUtterance(chunk.trim());
        const voices = window.speechSynthesis.getVoices();
        const premiumVoices = voices.filter(v => 
          v.lang.startsWith('en') && 
          (v.name.includes("Premium") || v.name.includes("Natural") || v.name.includes("Google") || v.name.includes("Samantha"))
        );
        const bestVoice = premiumVoices[0] || voices.find(v => v.lang.startsWith('en')) || voices[0];
        
        if (bestVoice) utterance.voice = bestVoice;
        utterance.rate = 1.05; // Slightly faster for urgency
        utterance.pitch = 1.0;
        
        // Only trigger the chrome fix resume if we're not on the last chunk
        utterance.onend = () => {
            if (index < chunks.length - 1) window.speechSynthesis.resume();
        };
        
        window.speechSynthesis.speak(utterance);
    });
  };


  // Prime TTS for mobile (iOS Safari requires this on first user interaction)
  const primeTTS = () => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance("");
      window.speechSynthesis.speak(utterance);
    }
  };

  useEffect(() => {
    setHasMounted(true);
    
    // Auto-enable demo mode if not on localhost
    if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
       setIsDemoMode(true);
    }
    
    // Pre-load voices for mobile
    if ('speechSynthesis' in window) {
        const loadVoices = () => {
          window.speechSynthesis.getVoices();
        };
        loadVoices();
        if (window.speechSynthesis.onvoiceschanged !== undefined) {
          window.speechSynthesis.onvoiceschanged = loadVoices;
        }
    }

    // CHROME BUG WORKAROUND: Chrome's speechSynthesis gets "stuck" after long 
    // utterances. This interval keeps it alive by periodically calling resume().
    const chromeTTSFix = setInterval(() => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.resume();
      }
    }, 10000);

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const isLocalhostDev = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.port === '3000';
    const wsUrl = isLocalhostDev 
        ? "ws://localhost:8000/ws/dispatcher" 
        : `${protocol}//${window.location.host}/ws/dispatcher`;
        
    const socket = new WebSocket(wsUrl);
    
    socket.onopen = () => {
      setStatus("ONLINE");
      setWs(socket);
    };
    
    socket.onclose = () => {
      setStatus("OFFLINE");
      setWs(null);
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "agent_response") {
        setLastResponse(data.response);
        if (data.user_text) setLastTranscription(data.user_text);
        speakResponse(data.response);

        if (data.inventory) setInventory(data.inventory);
        if (data.new_alert) {
            setAlerts(prev => [data.new_alert, ...prev].slice(0, 2));
        }
      }
    };
    return () => {
        socket.close();
        stopCamera();
        clearInterval(chromeTTSFix);
    };
  }, []);

  const handleDispatch = async () => {
    primeTTS(); // Unlock audio on mobile
    
    if (isDemoMode) {
      if (!isDemoMicActive) {
        setIsDemoMicActive(true);
        setStagedImage(null);
        setLastResponse("ANALYZING FIELD DATA...");
        setLastTranscription("Listening...");
      } else {
        setIsDemoMicActive(false);
        setLastResponse("PROCESSING [GEMMA 4]...");
        
        // Fire Demo Scenario
        setTimeout(() => {
          const scenario = DEMO_SCENARIOS[demoIndex];
          setLastTranscription(scenario.user_text);
          setLastResponse(scenario.response);
          speakResponse(scenario.response);
          if (scenario.inventory) setInventory(scenario.inventory);
          if (scenario.new_alert) setAlerts(prev => [scenario.new_alert, ...prev].slice(0, 2));
          setDemoIndex((prev) => (prev + 1) % DEMO_SCENARIOS.length);
        }, 1500);
      }
      return;
    }

    if (!ws || ws.readyState !== WebSocket.OPEN) {
      setLastResponse("CRITICAL: SYSTEM OFFLINE. Ensure backend server is running on port 8000.");
      return;
    }
    if (!isMicActive) {
      // Automatic camera start removed for cleaner demo recording
      startRecording(stagedImage);
      setStagedImage(null);
      setLastResponse("ANALYZING FIELD DATA...");
      setLastTranscription("Listening...");
    } else {
      stopRecording();
      setLastResponse("PROCESSING [GEMMA 4]...");
    }
  };

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    primeTTS(); // Unlock audio on mobile
    
    if (isDemoMode && inputText.trim()) {
      setLastTranscription(inputText);
      setInputText("");
      setStagedImage(null);
      setLastResponse("PROCESSING FIELD NOTES...");
      
      setTimeout(() => {
        const scenario = DEMO_SCENARIOS[demoIndex];
        setLastTranscription(scenario.user_text);
        setLastResponse(scenario.response);
        speakResponse(scenario.response);
        if (scenario.inventory) setInventory(scenario.inventory);
        if (scenario.new_alert) setAlerts(prev => [scenario.new_alert, ...prev].slice(0, 2));
        setDemoIndex((prev) => (prev + 1) % DEMO_SCENARIOS.length);
      }, 1000);
      return;
    }

    if (ws && inputText.trim()) {
      ws.send(JSON.stringify({ text: inputText, image: stagedImage }));
      setLastTranscription(inputText);
      setInputText("");
      setStagedImage(null);
      setLastResponse("PROCESSING FIELD NOTES...");
    }
  };

  if (!hasMounted) return <div className="h-[100dvh] w-full bg-black" />;

  return (
    <main className="flex flex-col h-[100dvh] bg-black text-white selection:bg-primary/30 overflow-hidden relative">
      
      {/* 1. STATUS HEADER */}
      <header className="shrink-0 p-4 border-b border-white/10 flex justify-between items-center bg-zinc-950/50">
        <div className="flex flex-col">
            <h1 className="text-lg font-black tracking-tighter text-white">GEMMAVOICE</h1>
            <span className="text-[8px] font-bold tracking-[0.4em] text-primary opacity-80">V1.1 FIELD BUILD</span>
        </div>
        <div className="flex gap-2">
            <button 
                onClick={() => {
                    setIsDemoMode(!isDemoMode);
                }}
                className={`px-3 py-1 text-[10px] font-bold border rounded transition-colors ${isDemoMode ? 'bg-primary text-black border-primary shadow-[0_0_10px_rgba(250,204,21,0.4)]' : 'border-white/20 hover:border-primary/50'}`}
            >
                {isDemoMode ? 'DEMO ACTIVE' : 'DEMO MODE'}
            </button>
            {iCameraActive && !isQuietMode && (
                <button 
                    onClick={() => stopCamera()}
                    className="px-3 py-1 text-[10px] font-bold border border-alert text-alert rounded hover:bg-alert/10 transition-colors"
                >
                    STOP CAMERA
                </button>
            )}
            <button 
                onClick={() => {
                    const newMode = !isQuietMode;
                    setIsQuietMode(newMode);
                    if (newMode) stopCamera();
                }}
                className={`px-3 py-1 text-[10px] font-bold border rounded transition-colors ${isQuietMode ? 'bg-primary text-black border-primary' : 'border-white/20'}`}
            >
                {isQuietMode ? 'QUIET MODE' : 'VOICE MODE'}
            </button>
            <div className={`px-2 py-1 text-[10px] font-bold border rounded ${status === 'ONLINE' ? 'text-safe border-safe' : 'text-alert border-alert animate-pulse'}`}>
                {status}
            </div>
        </div>
      </header>

      {/* 2. CAMERA VIEWFINDER (CENTERPIECE) */}
      <section className="relative flex-1 bg-zinc-900 overflow-hidden flex items-center justify-center">
        {!iCameraActive && (
            <div className="absolute inset-0 flex flex-col items-center justify-center opacity-50 z-0">
                <span className="text-4xl mb-4">📷</span>
                <p className="text-xs font-mono uppercase tracking-widest text-[#facc15]">Camera Inactive</p>
                <p className="text-[10px] uppercase text-white/50 mt-2 text-center px-8">Press DISPATCH to activate Visual Forensics</p>
            </div>
        )}
        <video 
            ref={videoRef} 
            autoPlay 
            playsInline 
            muted 
            className="absolute inset-0 w-full h-full object-cover grayscale-[0.3] contrast-125 z-10"
        />
        <canvas ref={canvasRef} className="hidden" />
        
        {/* VIEWPORT OVERLAYS */}
        <div className="absolute inset-0 pointer-events-none p-4 flex flex-col justify-between z-30">
            {/* Top Corners */}
            <div className="flex justify-between items-start w-full">
                <div className="w-6 h-6 border-t-2 border-l-2 border-primary/60" />
                <div className="w-6 h-6 border-t-2 border-r-2 border-primary/60" />
            </div>

            {/* Bottom Corners */}
            <div className="flex flex-col items-center w-full">
                {lastTranscription && !lastResponse && (
                    <div className="bg-black/60 backdrop-blur-md text-white/90 px-3 py-1.5 rounded-full text-[10px] font-medium border border-white/10 shadow-2xl mb-4 max-w-[85%] text-center italic">
                        "{lastTranscription}"
                    </div>
                )}
                <div className="flex justify-between items-end w-full">
                    <div className="w-6 h-6 border-b-2 border-l-2 border-primary/60" />
                    <div className="w-6 h-6 border-b-2 border-r-2 border-primary/60" />
                </div>
            </div>
        </div>
      </section>

      {/* 3. INTERACTION DOCK */}
      <footer className="shrink-0 bg-black/90 backdrop-blur-xl border-t border-white/10 p-6 pb-10 relative z-50 pointer-events-auto">
        
        {isQuietMode ? (
            <form onSubmit={handleManualSubmit} className="flex gap-2">
                <input 
                    type="text" 
                    autoFocus
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Enter manual request..."
                    className="flex-1 bg-zinc-900 border border-white/20 rounded-xl px-4 py-4 text-base focus:border-primary outline-none transition-all"
                />
                <button type="submit" className="bg-primary text-black font-black px-6 rounded-xl uppercase text-sm tracking-tighter shadow-[0_0_15px_rgba(250,204,21,0.4)]">Send</button>
            </form>
        ) : (
            <div className="flex flex-col items-center relative">
                {/* Thumbnail Preview Area - Floating & Glowing */}
                <div className="h-20 flex items-center justify-center mb-4 w-full">
                    {stagedImage && (
                        <div className="relative border-2 border-primary rounded-xl overflow-hidden h-full shadow-[0_0_20px_rgba(250,204,21,0.3)] animate-in zoom-in-95 duration-200">
                            <img src={`data:image/jpeg;base64,${stagedImage}`} className="h-full w-auto object-cover" />
                            <button onClick={() => setStagedImage(null)} className="absolute top-1 right-1 bg-black/80 w-6 h-6 flex items-center justify-center rounded-full text-[10px] border border-white/20">✕</button>
                        </div>
                    )}
                </div>

                <div className="flex gap-10 items-center justify-center w-full px-4">
                    {/* SNAPSHOT BUTTON - LARGER & STYLIZED */}
                    <button 
                        onClick={async () => {
                            if (!iCameraActive) {
                                await startCamera();
                            } else {
                                const frame = captureFrame();
                                if (frame) setStagedImage(frame);
                            }
                        }}
                        className={`w-16 h-16 rounded-2xl border-2 flex flex-col items-center justify-center bg-zinc-900 transition-all ${iCameraActive ? 'border-primary/60 text-primary' : 'border-white/20'}`}
                    >
                        <span className="text-2xl">{iCameraActive ? "📸" : "📷"}</span>
                        <span className="text-[7px] font-black tracking-widest mt-0.5 opacity-60">
                            {iCameraActive ? 'SNAP' : 'CAMERA'}
                        </span>
                    </button>


                    {/* DISPATCH / MIC BUTTON - PREMIUM GLOW */}
                    <div className="flex flex-col items-center">
                        <button 
                            onClick={handleDispatch}
                            className={`relative w-24 h-24 rounded-full border-4 flex items-center justify-center transition-all duration-300 ${isMicActive ? 'border-alert bg-alert scale-110 shadow-[0_0_40px_rgba(239,68,68,0.6)]' : 'border-primary bg-primary shadow-[0_0_25px_rgba(250,204,21,0.4)] hover:scale-105 active:scale-95'}`}
                        >
                            <div className={`w-20 h-20 rounded-full border-4 border-black/10 flex items-center justify-center`}>
                                <span className="text-3xl">{isMicActive ? "⏹" : "🎙"}</span>
                            </div>
                            {isMicActive && <div className="absolute inset-[-10px] border-2 border-alert rounded-full animate-ping opacity-30" />}
                        </button>
                    </div>
                    
                    {/* QUIET MODE QUICK ACCESS */}
                    <button 
                        onClick={() => setIsQuietMode(true)}
                        className="w-16 h-16 rounded-2xl border-2 border-white/20 flex flex-col items-center justify-center bg-zinc-900 hover:bg-zinc-800 active:scale-95 transition-all"
                    >
                        <span className="text-2xl">⌨️</span>
                        <span className="text-[7px] font-black tracking-widest mt-0.5 opacity-60">TEXT</span>
                    </button>
                </div>
                
                <span className={`mt-4 text-[10px] font-black tracking-[0.3em] uppercase transition-opacity duration-500 ${isMicActive ? 'text-alert animate-pulse' : 'text-white/40'}`}>
                    {isMicActive ? 'LISTENING TO FIELD DATA' : 'PUSH TO DISPATCH'}
                </span>
            </div>
        )}

        {/* BOTTOM HUD: REDESIGNED FOR READABILITY */}
        <div className="mt-8 space-y-3">
            {/* ALERT QUEUE - PROMINENT */}
            <div className="bg-zinc-900/80 border border-white/10 p-3 rounded-xl backdrop-blur-md">
                <div className="flex justify-between items-center mb-2">
                    <p className="text-[10px] font-black text-primary tracking-widest uppercase">Live Alert Queue</p>
                    <div className="w-2 h-2 rounded-full bg-safe animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.5)]" />
                </div>
                <div className="space-y-2">
                    {alerts.map((alert, idx) => (
                        <div key={idx} className={`p-3 rounded-lg border-l-4 text-xs font-bold leading-tight ${alert.style === 'alert' ? 'bg-alert/10 border-alert text-alert' : 'bg-safe/10 border-safe text-safe'}`}>
                            {alert.msg}
                        </div>
                    ))}
                </div>
            </div>

            {/* LOCAL STOCK - GRID LAYOUT */}
            <div className="bg-zinc-900/80 border border-white/10 p-3 rounded-xl backdrop-blur-md">
                <p className="text-[10px] font-black text-primary tracking-widest uppercase mb-3 text-center border-b border-white/5 pb-2">Resource Telemetry</p>
                <div className="grid grid-cols-3 gap-2">
                    {inventory.slice(0, 6).map((item, idx) => (
                        <div key={idx} className="flex flex-col items-center p-2 rounded-lg bg-black/40 border border-white/5">
                            <span className="text-[14px] font-black text-white">{item.qty}</span>
                            <span className="text-[8px] font-bold text-white/40 uppercase truncate w-full text-center">{item.name}</span>
                        </div>
                    ))}
                    {inventory.length === 0 && (
                        <div className="col-span-3 text-center py-2 text-[10px] text-white/20 italic">No telemetry data available</div>
                    )}
                </div>
            </div>
        </div>
      </footer>
      {/* 4. GLOBAL PROTOCOL OVERLAY */}
      <div className="fixed inset-0 z-[100] pointer-events-none flex items-start justify-center p-6 pt-24 pb-[300px]">
          {lastResponse && (
              <div className="w-full max-w-[450px] max-h-full pointer-events-auto flex flex-col backdrop-blur-3xl bg-black/95 p-6 border-2 border-primary/50 rounded-3xl shadow-[0_0_100px_rgba(250,204,21,0.2)] animate-in fade-in zoom-in-95 duration-300">
                  <div className="flex items-center justify-between shrink-0 mb-4 border-b border-white/10 pb-3">
                      <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                          <span className="text-primary text-[10px] font-black uppercase tracking-widest">CRITICAL PROTOCOL ACTIVE</span>
                      </div>
                      <button 
                        onClick={() => setLastResponse("")} 
                        className="text-white/40 hover:text-white hover:bg-white/10 text-[10px] uppercase font-bold px-3 py-1.5 bg-white/5 rounded-lg transition-colors"
                      >
                        Dismiss
                      </button>
                  </div>
                  <div className="overflow-y-auto flex-1 pr-3 custom-scrollbar min-h-0">
                      {lastTranscription && lastTranscription !== "Listening..." && (
                          <div className="mb-4 pb-4 border-b border-white/10">
                              <p className="text-primary/70 text-[10px] uppercase font-black tracking-widest mb-1">FIELD CAPTURE</p>
                              <p className="text-white/80 text-sm italic">"{lastTranscription}"</p>
                          </div>
                      )}
                      <p className="text-primary/70 text-[10px] uppercase font-black tracking-widest mb-1">GEMMA 4 ANALYSIS</p>
                      <p className="text-left text-sm font-semibold leading-relaxed text-white whitespace-pre-wrap">
                          {lastResponse}
                      </p>
                  </div>
              </div>
          )}
      </div>
    </main>
  );
}

