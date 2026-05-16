"""
GemmaVoice — Dispatcher Engine v2.0
ReAct Pipeline: text → LLM → tool execution → LLM synthesis → response.
Dynamic Model Routing: e4b (text) / 26b (vision).
"""
import ollama
from tools import init_db, TOOL_REGISTRY, TOOL_SPEC, get_all_inventory

# --- CONFIGURATION ---
TEXT_MODEL = "gemma4:e4b"
VISION_MODEL = "gemma4:26b"

SYSTEM_PROMPT = (
    "CRITICAL PROTOCOL: You are the GemmaVoice Emergency Dispatcher. "
    "You are working OFFLINE in a disaster zone. "
    "MISSION: Save lives by combining Tools, Knowledge, and Reasoning.\n"
    "VISUAL ANALYSIS MANDATE:\n"
    "1. If you see structural damage (cracks, spalling, debris), you MUST call 'consult_protocol' with 'structural collapse'.\n"
    "2. If you see medical trauma, you MUST call 'perform_triage'.\n"
    "3. NEVER provide a final safety decision without calling a tool first.\n"
    "RESPONSE STYLE: Be extremely concise. Use bold headers. Speak like a field commander.\n"
)



def _detect_models() -> dict:
    """Detects which Gemma models are available on the local machine."""
    available = {"text": TEXT_MODEL, "vision": VISION_MODEL}
    try:
        response = ollama.list()
        model_names = [m.model for m in response.models]

        # Find text model
        for m in model_names:
            if m.startswith(TEXT_MODEL):
                available["text"] = m
                break

        # Find vision model
        for m in model_names:
            if "26b" in m:
                available["vision"] = m
                break

    except Exception as e:
        print(f"Model detection error: {e}")

    return available


class GemmaDispatcher:
    def __init__(self):
        init_db()
        self.models = _detect_models()
        print(f"Brain active — Text: {self.models['text']}, Vision: {self.models['vision']}")

    def _select_model(self, has_image: bool) -> str:
        """Route to the right model based on the request type."""
        if has_image:
            print(f"DEBUG [Model Routing]: Image detected → using VISION model ({self.models['vision']})")
            return self.models["vision"]
        return self.models["text"]

    def execute(self, text: str, memory: list, image_bytes: bytes = None) -> tuple:
        """
        ReAct Pipeline:
        1. LLM decides which tools to call
        2. Tools execute
        3. LLM synthesizes tool results into a natural response
        Returns (response_text: str, alert: dict | None).
        """
        model = self._select_model(has_image=image_bytes is not None)

        user_message = {"role": "user", "content": text}
        if image_bytes:
            user_message["images"] = [image_bytes]

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(memory[-10:])
        messages.append(user_message)

        # --- STEP 1: Tool Selection ---
        response = ollama.chat(
            model=model,
            messages=messages,
            tools=TOOL_SPEC
        )

        print(f"DEBUG [Step 1 - Tool Selection]: {response.get('message', {}).get('tool_calls', 'No tools')}")

        message = response.get('message', {})
        new_alert = None

        if not message.get('tool_calls'):
            # No tools needed — return direct LLM response
            return message.get('content', "No response generated."), None

        # --- STEP 2: Tool Execution ---
        tool_results = []
        for call in message['tool_calls']:
            func_name = call['function']['name']
            args = call['function']['arguments']
            if func_name in TOOL_REGISTRY:
                result = TOOL_REGISTRY[func_name](**args)
                print(f"DEBUG [Step 2 - Tool Exec]: {func_name}({args}) → {result}")
                tool_results.append({"tool": func_name, "args": args, "result": result})

                # Capture visual alerts for the HUD
                if func_name == "broadcast_mesh_alert":
                    new_alert = {"title": "MESH BROADCAST", "msg": args.get('message', 'Alert'), "style": "alert"}
                elif func_name == "perform_triage":
                    new_alert = {"title": "TRIAGE LOG", "msg": result, "style": "safe"}
                elif func_name == "register_victim":
                    new_alert = {"title": "VICTIM REGISTERED", "msg": result, "style": "safe"}

        # --- STEP 3: ReAct Synthesis ---
        # Feed the tool results back to the LLM for a natural, interpreted response
        tool_summary = "\n".join(
            [f"[{r['tool']}] → {r['result']}" for r in tool_results]
        )

        # UI Enhancement: If we found a protocol, push it to the Live Alert queue too
        if not new_alert:
            for r in tool_results:
                if r['tool'] == 'consult_protocol' and "Found Protocol" in r['result']:
                    short_msg = r['result'].split("PROTOCOL]:")[1].strip()
                    if len(short_msg) > 70: short_msg = short_msg[:67] + "..."
                    new_alert = {"title": "PROTOCOL RETRIEVED", "msg": short_msg, "style": "alert"}

        synthesis_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
            {"role": "assistant", "content": f"I executed the following tools:\n{tool_summary}"},
            {"role": "user", "content": (
                "Now synthesize these tool results into a structured field response using this EXACT format:\n"
                "**SUMMARY:** (One sentence summarizing the situation)\n"
                "**PROTOCOL:** (Numbered list of immediate actions)\n"
                "**LOGISTICS:** (Any inventory or manifest data retrieved)\n"
                "Be extremely concise. Use bold headers. Do not repeat raw tool data verbatim."
            )}
        ]

        try:
            synthesis = ollama.chat(
                model=self.models["text"],  # Always use fast model for synthesis
                messages=synthesis_messages
            )
            content = synthesis.get('message', {}).get('content', tool_summary)
            print(f"DEBUG [Step 3 - Synthesis]: {content[:200]}...")
        except Exception as synth_err:
            print(f"Synthesis fallback (error: {synth_err})")
            content = tool_summary

        return content, new_alert
