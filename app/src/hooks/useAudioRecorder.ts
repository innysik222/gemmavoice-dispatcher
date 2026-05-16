import { useState, useCallback, useRef } from 'react';

/**
 * GEMMAVOICE HYBRID AUDIO CAPTURE
 * Uses Web Speech API for fast native transcription to bypass edge audio bottlenecks.
 */
export const useAudioRecorder = (ws: WebSocket | null) => {
  const [isRecording, setIsRecording] = useState(false);
  const [liveText, setLiveText] = useState('');
  const recognitionRef = useRef<any>(null);
  const transcriptRef = useRef<string>('');
  const interimRef = useRef<string>('');

  const activeImageRef = useRef<string | null>(null);

  const startRecording = useCallback((image: string | null = null) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    
    // Store image for final pairing
    activeImageRef.current = image;

    // @ts-ignore
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn("Speech API not supported in this browser. Falling back to text.");
      alert("Voice capabilities are not supported by this browser. Please use the text input.");
      return;
    }

    transcriptRef.current = '';
    interimRef.current = '';
    setLiveText('');
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US'; // Re-enforced to prevent STT auto-detect hallucinations
    
    recognition.onresult = (event: any) => {
      let finalTranscript = '';
      let currentInterim = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          currentInterim += event.results[i][0].transcript;
        }
      }
      if (finalTranscript) {
        transcriptRef.current += finalTranscript + ' ';
      }
      interimRef.current = currentInterim;
      setLiveText((transcriptRef.current + " " + currentInterim).trim());
    };

    recognition.onerror = (event: any) => {
      console.error("Speech recognition error", event.error);
      alert("Microphone Error: " + event.error + ". Please ensure you have granted microphone permissions and are accessing the site via localhost or HTTPS.");
      setIsRecording(false);
    };

    try {
      recognition.start();
      recognitionRef.current = recognition;
      setIsRecording(true);
    } catch (err) {
      console.error("Speech Recognition failed to start:", err);
      alert("Microphone Access Error: Could not start voice capture. Please check your browser permissions.");
      setIsRecording(false);
    }
  }, [ws]);

  const stopRecording = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setIsRecording(false);
    
    // Slight delay to ensure final audio buffer results are caught
    setTimeout(() => {
      const text = (transcriptRef.current + " " + interimRef.current).trim();
      const image = activeImageRef.current;
      setLiveText("");
      
      if (ws && ws.readyState === WebSocket.OPEN) {
        if (text.length > 0) {
          console.log("Transcribed Audio + Context sent to backend:", text);
          ws.send(JSON.stringify({ type: 'text', text: text, image: image }));
        } else {
          // If browser recorded pure silence or failed to catch anything, tell backend to clear UI
          console.warn("Audio was empty. Sending fallback clear.");
          ws.send(JSON.stringify({ type: 'text', text: "System Error: The user's microphone did not capture any words. Reply exactly with: 'Audio was too quiet or unclear. Please try speaking closer to the mic.'" }));
        }
      }
      activeImageRef.current = null; // Clear image after send
    }, 500);
  }, [ws]);

  return { isRecording, liveText, startRecording, stopRecording };
};
