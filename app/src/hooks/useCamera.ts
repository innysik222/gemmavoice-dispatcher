import { useState, useCallback, useRef } from 'react';

/**
 * useCamera
 * Manages the mobile camera stream and provides frame capture for vision triage.
 */
export const useCamera = () => {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const startCamera = useCallback(async () => {
    try {
      const constraints = {
        video: true
      };
      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err) {
      console.error("Camera access denied:", err);
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
  }, [stream]);

  const captureFrame = useCallback((): string | null => {
    if (!videoRef.current || !canvasRef.current) return null;
    
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');
    
    if (context) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      // Convert to Base64 (JPEG for smaller payload)
      return canvas.toDataURL('image/jpeg', 0.8).split(',')[1];
    }
    return null;
  }, []);

  return {
    videoRef,
    canvasRef,
    startCamera,
    stopCamera,
    captureFrame,
    isActive: !!stream
  };
};
