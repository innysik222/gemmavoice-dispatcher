import ollama
import json

# --- CONFIGURATION ---
MODEL = "gemma4:26b" # Using the already present 26b for high-quality multilingual reasoning

TEST_CASES = [
    {
        "lang": "Spanish",
        "input": "¿Cuántas botellas de agua nos quedan en el almacén?",
        "expected_tool": "check_inventory",
        "expected_arg": "agua"
    },
    {
        "lang": "French",
        "input": "Nous avons un blessé grave, il ne respire plus. Marquez-le comme priorité rouge.",
        "expected_tool": "perform_triage",
        "expected_arg": "RED"
    },
    {
        "lang": "Hindi",
        "input": "हमारे पास कितनी पट्टियाँ बची हैं?", # "How many bandages do we have left?"
        "expected_tool": "check_inventory",
        "expected_arg": "pattiyan" or "bandages"
    }
]

def run_multilingual_test():
    print("--- GEMMAVOICE MULTILINGUAL VALIDATION ---")
    for case in TEST_CASES:
        print(f"\n[TEST] {case['lang']}: \"{case['input']}\"")
        
        response = ollama.chat(
            model=MODEL,
            messages=[{
                "role": "user", 
                "content": f"You are an emergency dispatcher. Analyze this command and call the correct tool: {case['input']}"
            }],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "check_inventory",
                        "parameters": {
                            "type": "object",
                            "properties": {"item": {"type": "string"}}
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "perform_triage",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "resp_rate": {"type": "integer"},
                                "perfusion": {"type": "boolean"},
                                "mental_status": {"type": "boolean"}
                            }
                        }
                    }
                }
            ]
        )
        
        # Validation
        if response.get('message', {}).get('tool_calls'):
            tool_name = response['message']['tool_calls'][0]['function']['name']
            args = response['message']['tool_calls'][0]['function']['arguments']
            print(f"✅ Success: Triggered {tool_name} with {args}")
        else:
            print(f"❌ Failed: No tool called. Response: {response['message']['content']}")

if __name__ == "__main__":
    run_multilingual_test()
