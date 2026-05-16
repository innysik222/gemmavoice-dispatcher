import { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'GemmaVoice Emergency Dispatcher',
    short_name: 'GemmaVoice',
    description: 'Offline-First, Voice-Activated Crisis Manager.',
    start_url: '/',
    display: 'standalone',
    background_color: '#111827',
    theme_color: '#FBBF24',
    icons: [
      {
        src: '/icon.png',
        sizes: '512x512',
        type: 'image/png',
      },
    ],
  }
}
