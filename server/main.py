"""
GemmaVoice — WebSocket Server
Thin transport layer. All logic lives in dispatcher.py and tools.py.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dispatcher import GemmaDispatcher
from tools import get_all_inventory
import json
import asyncio
import uvicorn

app = FastAPI(title="GemmaVoice API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

dispatcher = GemmaDispatcher()

@app.get("/status")
async def get_status():
    return {"status": "GemmaVoice System Online", "model": dispatcher.model}

# Global session storage to survive mobile tunnel reconnections
# In a real production app, this would be in Redis or SQLite
SESSION_STORE = {}

@app.websocket("/ws/dispatcher")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Unique session key (could be IP or a generated ID, for now we use a single global key for the hackathon demo)
    session_id = "global_session" 
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = []
    
    print(f"Crisis Dispatcher connected. Resuming session: {session_id}")
    session_memory = SESSION_STORE[session_id]

    try:
        while True:
            message = await websocket.receive()

            if "text" not in message:
                continue

            text_data = json.loads(message["text"])
            command_text = text_data.get("text", "").strip()
            image_b64 = text_data.get("image") # Optional Base64 image
            image_bytes = None

            if image_b64:
                import base64
                try:
                    image_bytes = base64.b64decode(image_b64)
                    print(f"DEBUG [Image Received]: {len(image_bytes)} bytes")
                except Exception as b64err:
                    print(f"B64 Decode Error: {b64err}")

            if not command_text:
                continue

            print(f"DEBUG [Command]: {command_text}")

            # Noise Filtering: Don't process STT errors via LLM, and don't save them to memory
            if "System Error" in command_text:
                await websocket.send_json({
                    "response": "Audio was too quiet or unclear. Please try speaking closer to the mic.",
                    "type": "agent_response",
                    "inventory": get_all_inventory()
                })
                continue

            try:
                response_content, new_alert = await asyncio.to_thread(
                    dispatcher.execute, command_text, session_memory, image_bytes
                )

                # Update session memory (ONLY for real commands)
                session_memory.append({"role": "user", "content": command_text})
                session_memory.append({"role": "assistant", "content": response_content})

            except Exception as llm_err:
                print(f"LLM Processing Error: {llm_err}")
                response_content = f"Critical Error: Local Intelligence Engine Offline. Details: {llm_err}"
                new_alert = None

            # Send response to frontend
            try:
                payload = {
                    "response": response_content,
                    "user_text": command_text,
                    "type": "agent_response",
                    "inventory": get_all_inventory()
                }
                if new_alert:
                    payload["new_alert"] = new_alert
                    
                await websocket.send_json(payload)
            except Exception as e:
                print(f"Failed to send response: {e}")
            
    except WebSocketDisconnect:
        print("Dispatcher disconnected.")
    except Exception as e:
        print(f"Error in WebSocket: {e}")
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
