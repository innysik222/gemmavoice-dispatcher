# GemmaVoice — Autonomous Disaster Dispatch

> When the world goes dark, intelligence stays on.

GemmaVoice is a hands-free, offline-first emergency dispatcher built for first responders operating in disaster zones with zero connectivity. It runs entirely on-device using Gemma 4 via Ollama, with no cloud dependency whatsoever.

I built this for the [Kaggle Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good) because I kept thinking about one scenario: a medic in a collapsed building, hands busy, no cell signal, needing expert guidance *right now*. That's the problem GemmaVoice solves.

## What It Does

GemmaVoice is not a chatbot. It's an **agentic system** that reasons about what tools to use based on your voice input:

- **Protocol Intelligence** — Ask about a chlorine leak, and it retrieves the exact evacuation procedure from a local protocol database. No internet needed.
- **Resource Telemetry** — Say "we just received 200 liters of water" and the inventory updates in real-time across the UI.
- **Visual Forensics** — Point your camera at structural damage, and the 26B vision model identifies shear cracks, spalling, and rebar exposure to assess safety.

All of this happens through voice. You speak, Gemma thinks, tools execute, and you hear the answer read back to you.

## How It Works

The core is a **ReAct (Reasoning + Acting) pipeline**:

```
Voice Input → Speech-to-Text → Gemma 4 (Tool Selection) → Tool Execution → Gemma 4 (Synthesis) → Text-to-Speech
```

1. Your voice is transcribed using the Web Speech API
2. The transcript hits Gemma 4, which decides *which tools to call* (not hardcoded — the model reasons about it)
3. Tools run against a local SQLite database (inventory checks, protocol lookups, triage scoring)
4. Tool results go back to Gemma 4 for a natural, structured response
5. The response is spoken back to you and displayed on the HUD

**Model routing** happens automatically:
- Text-only queries → **Gemma 4 (4B)** for fast responses
- Image + text queries → **Gemma 4 (26B)** for visual forensics

## The Tools

| Tool | What It Does |
|------|-------------|
| `consult_protocol` | Looks up emergency SOPs (chlorine, radiation, flooding, burns, structural collapse, cyanide) |
| `check_inventory` | Queries local supply levels |
| `update_inventory` | Adjusts stock counts via voice (restock or spend) |
| `perform_triage` | Runs the START triage algorithm with optional visual override |
| `register_victim` | Logs survivors into a local field manifest |
| `search_victims` | Searches the manifest by name or location |
| `broadcast_mesh_alert` | Simulates peer-to-peer emergency broadcasts |

## Tech Stack

- **Models**: Gemma 4 (e4b for text, 26b for vision) via [Ollama](https://ollama.com)
- **Backend**: Python / FastAPI / WebSocket
- **Frontend**: Next.js / TypeScript / Tailwind CSS
- **Database**: SQLite (local, no server)
- **Speech**: Web Speech API (browser-native STT + TTS)

## Setup

### Prerequisites
- [Ollama](https://ollama.com) installed
- Node.js 18+
- Python 3.10+

### 1. Pull the models
```bash
ollama pull gemma4:e4b
ollama pull gemma4:26b    # optional, requires ~16GB RAM
```

### 2. Start the backend
```bash
cd server
pip install -r requirements.txt
python main.py
```

### 3. Start the frontend
```bash
cd app
npm install
npm run dev
```

### 4. Open the app
Navigate to `http://localhost:3000` on your phone or browser. For mobile access over your local network, use your machine's IP address.

## Why Offline?

This isn't offline because it's trendy. It's offline because in a real disaster:
- Cell towers are the first infrastructure to fail
- Cloud APIs have latency that kills in triage scenarios
- Patient data in a disaster zone shouldn't travel through third-party servers
- Responders need something that works when literally everything else doesn't

GemmaVoice is designed to run on a local server at a distribution center, with field teams connecting via a local mesh network. The 26B model handles deep analysis at the hub, while 4B handles fast decisions at the edge.

## Project Structure

```
gemmavoice-dispatcher/
├── app/                    # Next.js frontend
│   └── src/
│       ├── app/page.tsx    # Main mobile dashboard UI
│       └── hooks/          # Audio recorder + Camera hooks
├── server/
│   ├── main.py             # FastAPI WebSocket server
│   ├── dispatcher.py       # ReAct pipeline + model routing
│   └── tools.py            # All tool functions + SQLite layer
├── data/
│   └── crisis.db           # Local SQLite database (auto-created)
└── tests/                  # Test suite
```

## Built For

**Kaggle Gemma 4 Good Hackathon**
- Track: Global Resilience
- Special Technology: Ollama

## License

MIT
