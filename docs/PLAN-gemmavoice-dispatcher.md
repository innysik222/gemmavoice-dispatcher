# PLAN: GemmaVoice - The Offline Emergency Dispatcher

One sentence: Building an offline-first, voice-activated emergency triage and resource coordinator using Gemma 4's native audio and function calling.

## 🔴 Project Type: WEB (Local-First Edge App)

## 🎯 Success Criteria
- [ ] User can speak to the browser/app (offline) and get an intelligent response.
- [ ] Gemma 4 correctly identifies "Emergency Triage" vs "Resource Request".
- [ ] Native Function Calling triggers local "Actions" (e.g., Inventory check, Mesh-alert simulation).
- [ ] Solution runs on local hardware using the E4B (Effective 4B) model.

## 🛠️ Tech Stack
- **AI Model**: Gemma 4 E4B (multimodal with native audio).
- **Inference Server**: Ollama (local) or `gemma.cpp`.
- **Frontend**: Next.js + React (Offline PWA capability).
- **Audio Interface**: Web Audio API (Stream to model).
- **Function Layer**: JSON-based function definitions for triage and resource coordination.

## 📂 Proposed File Structure
```plaintext
gemmavoice-dispatcher/
├── app/                  # Next.js frontend
├── server/               # Python/Node.js Agentic loop
│   ├── gemma_local.py    # Gemma 4 connector (native audio/functions)
│   └── tools/            # Definitions for triage, inventory, etc.
└── data/                 # Local SQLite/JSON for offline state
```

## 📋 Task Breakdown

### Phase 1: Analysis & Infrastructure
- [ ] **Task 1**: Setup local Ollama/Gemma.cpp with Gemma 4 E4B. → Verify: `ollama run gemma4:e4b` works.
- [ ] **Task 2**: Prototype Native Audio input pipe. → Verify: Can feed audio PCM data to model and get transcript/response.

### Phase 2: Agentic Logic (The "Dispatcher" Brain)
- [ ] **Task 3**: Define "Dispatcher Tools" (JSON Schema). → Verify: Model correctly selects tools based on voice input.
- [ ] **Task 4**: Implement Offline State (Inventories/Maps). → Verify: `find_resource("water")` returns local SQLite data.

### Phase 3: Hardware/UI Bridge
- [ ] **Task 5**: Build the "Crisis Interface" (High Contrast, Large Buttons). → Verify: Follows UX Audit rules (Fitts' Law for emergency use).
- [ ] **Task 6**: Implement "Mesh-Network Bridge" simulation. → Verify: Function call logs "Simulating Mesh Alert: Emergency at Grid X-42".

### Phase X: Final Verification
- [ ] **Task 7**: Run `verify_all.py` and security scans.
- [ ] **Task 8**: Record the "Winning" 3-minute Video Demo.

---

## ✅ PHASE X COMPLETE
- Lint: [ ]
- Security: [ ]
- Build: [ ]
- Date: [Current Date]
