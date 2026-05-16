"""
GemmaVoice — Tool Functions & Database Layer
All dispatcher tools, DB initialization, and tool spec definitions.
Single source of truth for the agentic pipeline.
"""
import os
import sqlite3

# Absolute path resolution for the database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "data", "crisis.db")


# --- UTILITIES ---

def sanitize_search_query(search_term: str) -> list:
    """Pure function. Extracts keywords and applies stopwords for DB searching."""
    ignore_words = {"hazard", "damage", "environmental", "type", "reported", "message", "emergency"}
    clean_words = [w.strip() for w in search_term.replace('/', ' ').split() if len(w) > 3 and w.strip().lower() not in ignore_words]
    return clean_words if clean_words else [search_term]


# --- DATABASE SETUP ---

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY,
            item_name TEXT UNIQUE,
            quantity INTEGER,
            unit TEXT,
            category TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS triage_logs (
            id INTEGER PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            status_tag TEXT,
            symptoms TEXT,
            location TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS protocols (
            id INTEGER PRIMARY KEY,
            topic TEXT,
            keywords TEXT,
            procedure TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS victims (
            id INTEGER PRIMARY KEY,
            name TEXT,
            location TEXT,
            status TEXT,
            notes TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Seed survival items if empty
    cursor.execute("SELECT count(*) FROM inventory")
    if cursor.fetchone()[0] == 0:
        items = [
            ('Water', 500, 'Liters', 'Essentials'),
            ('Sterile Bandages', 150, 'Units', 'Medical'),
            ('Insulin', 20, 'Vials', 'Medical'),
            ('Canned Food', 300, 'Units', 'Essentials'),
            ('Antibiotics', 45, 'Courses', 'Medical'),
            ('Hazmat Suits', 30, 'Units', 'Safety'),
            ('Respirators', 40, 'Units', 'Safety'),
        ]
        cursor.executemany("INSERT INTO inventory (item_name, quantity, unit, category) VALUES (?, ?, ?, ?)", items)

    # Seed emergency protocols if empty
    cursor.execute("SELECT count(*) FROM protocols")
    if cursor.fetchone()[0] == 0:
        protocols_data = [
            ('Chemical/Gas Hazard', 'smell, gas, chemical, chlorine, ammonia, methane, propane, bleach, sulfur, phosgene, mustard, sarin, leak, spill, fumes, toxic, hazardous, liquid, dizzy', 
             '1. Instruct personnel to EVACUATE UPWIND immediately. 2. DO NOT use electronics or light switches. 3. Establish a 500-meter perimeter. 4. Dispatch Hazmat unit. 5. Consult inventory for Respirators or Hazmat Suits. 6. If substance is heavier than air (e.g. chlorine), move to HIGH GROUND.'),
             
            ('Structural Collapse', 'earthquake, building, collapse, rubble, trapped, unstable', 
             '1. Establish isolation perimeter. 2. Implement "All Quiet" periods to listen for survivors. 3. DO NOT enter without structural engineers. 4. Check inventory for Shoring equipment and Medical Supplies.'),
             
            ('Severe Burns', 'burn, fire, heat, thermal, scald', 
             '1. Stop the burning process. 2. Cool the burn with running ambient water for 15-20 minutes. 3. DO NOT apply ice. 4. Cover with dry Sterile Bandages. 5. Check inventory for Sterile Bandages and Water.'),

            ('Radiation Exposure', 'radiation, radioactive, geiger, nuclear, glowing, contamination, fallout',
             '1. IMMEDIATE EVACUATION to 1-mile radius minimum. 2. Remove and bag all clothing. 3. Initiate full-body decontamination shower. 4. Do NOT touch the source. 5. Mark exclusion zone and request HAZMAT Nuclear Response Team.'),

            ('Flooding/Water Rise', 'flood, flooding, water, rising, submerged, drowning, dam',
             '1. Move to highest accessible ground immediately. 2. Do NOT walk through moving water. 3. Avoid electrical equipment and downed power lines. 4. Signal for rescue if trapped. 5. Monitor upstream dam reports if available.'),

            ('Cyanide Gas Exposure', 'cyanide, almond, bitter, almonds, prussic',
             '1. IMMEDIATE EVACUATION. Cyanide gas is characterized by a bitter almond smell. 2. DO NOT perform mouth-to-mouth CPR. 3. Administer Cyanokit (Hydroxocobalamin) immediately if available. 4. Wait for Level A Hazmat clearance.')
        ]
        cursor.executemany("INSERT INTO protocols (topic, keywords, procedure) VALUES (?, ?, ?)", protocols_data)
        
    conn.commit()
    conn.close()


# --- TOOL FUNCTIONS ---

def check_inventory(item: str) -> str:
    """Checks the local offline database for supply levels."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT quantity, unit FROM inventory WHERE item_name LIKE ?", (f"%{item}%",))
    result = cursor.fetchone()
    conn.close()
    if result:
        return f"Currently in stock: {result[0]} {result[1]}."
    return f"Sorry, {item} is not found in local inventory."


def perform_triage(resp_rate: int, perfusion: bool, mental_status: bool, is_walking: bool = False, visual_assessment: str = None) -> str:
    """
    Applies the START Triage protocol (Ground Truth).
    Integrated with Visual Forensics for multi-modal precision.
    """
    # 1. VISUAL OVERRIDE: If the Vision Analyst sees catastrophic injury, escalate regardless of vitals
    if visual_assessment:
        va_lower = visual_assessment.lower()
        critical_indicators = ["arterial", "hemorrhage", "amputation", "skull", "brain", "active bleeding", "charred", "3rd degree", "burn", "severe", "loss", "damage", "abrasion", "blood"]
        if any(word in va_lower for word in critical_indicators):
            return f"RED (Immediate) — Visual Forensics Alert: '{visual_assessment}'. Catastrophic trauma detected. Prioritize immediate evacuation/hemostatic control."

    # 2. START ALGORITHM (STANDARD)
    if is_walking:
        return "GREEN (Minor) — Walking wounded. Low priority. Direct to ambulatory care area. Monitor for delayed symptoms."
        
    if resp_rate == 0:
        return "BLACK (Deceased/Expectant) — No respirations detected. Tag and move to morgue staging. Do not expend resources."
        
    if resp_rate > 30:
        return "RED (Immediate) — Respiratory distress. Open airway, position recovery. Transport to surgical triage FIRST."
    
    if not perfusion:
        return "RED (Immediate) — No radial pulse, circulatory failure. Apply tourniquet if hemorrhaging. Elevate legs. Immediate transport."
    
    if not mental_status:
        return "RED (Immediate) — Unresponsive to commands, possible TBI. Stabilize C-spine. Do NOT move without backboard."
    
    return "YELLOW (Delayed) — Stable vitals but cannot self-evacuate. Splint fractures, manage pain. Transport when RED patients cleared."


def broadcast_mesh_alert(message: str, priority: str = "High") -> str:
    """Simulates a low-power mesh network broadcast to nearby units."""
    print(f"[MESH BROADCAST] [{priority}] {message}")
    return f"MESH ALERT SENT: {message} (Priority: {priority})"


def update_inventory(item: str, change: int) -> str:
    """Updates the inventory level for an item. Use negative numbers for usage/spending."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT quantity, unit FROM inventory WHERE item_name LIKE ?", (f"%{item}%",))
    result = cursor.fetchone()
    
    if not result:
        if change > 0:
            unit = "Units"
            cursor.execute("INSERT INTO inventory (item_name, quantity, unit, category) VALUES (?, ?, ?, 'General')", 
                           (item.capitalize(), change, unit))
            conn.commit()
            conn.close()
            return f"Found New Resource: {item.capitalize()} added to local stock. Current Total: {change} {unit}."
        else:
            conn.close()
            return f"Error: Item '{item}' not found in inventory. Cannot spend unknown resources."
    
    current_qty, unit = result
    new_qty = current_qty + change
    
    if new_qty < 0:
        conn.close()
        return f"Warning: Insufficient stock. Only {current_qty} {unit} available (requested change: {change}). Action cancelled."
    
    cursor.execute("UPDATE inventory SET quantity = ? WHERE item_name LIKE ?", (new_qty, f"%{item}%"))
    conn.commit()
    conn.close()
    
    action = "Used" if change < 0 else "Restocked"
    return f"Inventory Updated: {action} {abs(change)} {unit}. New Total: {new_qty} {unit}."


def consult_protocol(search_term: str = "", **kwargs) -> str:
    """Consults the emergency memory bank for standard operating procedures (SOPs)."""
    if not search_term and kwargs:
        search_term = str(list(kwargs.values())[0])
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    clean_words = sanitize_search_query(search_term)
        
    query_conditions = []
    params = []
    for word in clean_words:
        query_conditions.append("(topic LIKE ? OR keywords LIKE ?)")
        params.extend([f"%{word}%", f"%{word}%"])
        
    sql_query = "SELECT DISTINCT topic, procedure FROM protocols WHERE " + " OR ".join(query_conditions)
    
    try:
        cursor.execute(sql_query, params)
        results = cursor.fetchall()
    except Exception as e:
        print(f"RAG DB Error: {e}")
        results = []
        
    conn.close()
    
    if results:
        res_str = " | ".join([f"[{r[0]} PROTOCOL]: {r[1]}" for r in results])
        return f"Found Protocol(s): {res_str}"
    
    return f"No specific protocol found for '{search_term}'. Advise standard safety caution and request human Commander review."


def register_victim(name: str, location: str, status: str = "unknown", notes: str = "") -> str:
    """Registers a victim/survivor into the local field manifest database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO victims (name, location, status, notes) VALUES (?, ?, ?, ?)",
        (name, location, status, notes)
    )
    conn.commit()
    victim_id = cursor.lastrowid
    conn.close()
    return f"Victim registered — ID #{victim_id}: {name}, Location: {location}, Status: {status}. {notes}"


def search_victims(location: str = "", name: str = "") -> str:
    """Searches the victim manifest by location or name."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    conditions = []
    params = []
    if location:
        conditions.append("location LIKE ?")
        params.append(f"%{location}%")
    if name:
        conditions.append("name LIKE ?")
        params.append(f"%{name}%")
    
    if not conditions:
        cursor.execute("SELECT id, name, location, status, notes, timestamp FROM victims ORDER BY timestamp DESC LIMIT 10")
    else:
        cursor.execute(
            f"SELECT id, name, location, status, notes, timestamp FROM victims WHERE {' OR '.join(conditions)} ORDER BY timestamp DESC",
            params
        )
    
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        search_term = location or name or "all"
        return f"No victims found matching '{search_term}' in the field manifest."
    
    entries = []
    for r in results:
        entries.append(f"[ID#{r[0]}] {r[1]} — Location: {r[2]}, Status: {r[3]}, Notes: {r[4] or 'N/A'}, Logged: {r[5]}")
    return f"Field Manifest ({len(results)} found):\n" + "\n".join(entries)


def get_all_inventory() -> list:
    """Returns the full inventory state as a list for the UI to render."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, quantity, unit FROM inventory")
    inv = [{"name": row[0], "qty": row[1], "unit": row[2]} for row in cursor.fetchall()]
    conn.close()
    return inv


# --- TOOL REGISTRY ---

TOOL_REGISTRY = {
    "check_inventory": check_inventory,
    "update_inventory": update_inventory,
    "perform_triage": perform_triage,
    "broadcast_mesh_alert": broadcast_mesh_alert,
    "consult_protocol": consult_protocol,
    "register_victim": register_victim,
    "search_victims": search_victims,
}

TOOL_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "check_inventory",
            "description": "Check supply levels for items like water, food, or medicine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string", "description": "The name of the item to check."}
                },
                "required": ["item"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "perform_triage",
            "description": "Apply START triage protocol to a victim.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resp_rate": {"type": "integer", "description": "Respirations per minute. Use 0 if not breathing."},
                    "perfusion": {"type": "boolean", "description": "True if radial pulse is present."},
                    "mental_status": {"type": "boolean", "description": "True if victim follows commands."},
                    "is_walking": {"type": "boolean", "description": "Set True ONLY if the victim is independently walking around. If they have a broken leg, are trapped, or cannot move, set False."},
                    "visual_assessment": {"type": "string", "description": "Describe any visible traumatic injuries seen in the image, such as heavy bleeding, fractures, or burns."}
                },
                "required": ["resp_rate", "perfusion", "mental_status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_inventory",
            "description": "Adjust stock levels (subtract items used or add items restocked).",
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string", "description": "Item name (water, bandages, insulin)."},
                    "change": {"type": "integer", "description": "The amount spent (negative) or restocked (positive)."}
                },
                "required": ["item", "change"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "broadcast_mesh_alert",
            "description": "Send a critical alert to other rescue units without internet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The alert content."},
                    "priority": {"type": "string", "enum": ["Critical", "High", "Normal"]}
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_protocol",
            "description": "Look up emergency standard operating procedures. Use the substance name or hazard type directly as the search term.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_term": {"type": "string", "description": "The substance name or hazard type (e.g. 'chlorine', 'cyanide', 'earthquake', 'burn', 'radiation', 'flood')."}
                },
                "required": ["search_term"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "register_victim",
            "description": "Register a victim or survivor into the local field manifest database. Use this when a medic reports finding someone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Victim's name or identifier (e.g. 'John Doe', 'Unknown Male #3')."},
                    "location": {"type": "string", "description": "Where the victim was found (e.g. 'Sector 3', 'Building B Floor 2')."},
                    "status": {"type": "string", "description": "Current condition: 'responsive', 'unresponsive', 'critical', 'deceased', 'walking'."},
                    "notes": {"type": "string", "description": "Any additional observations about the victim."}
                },
                "required": ["name", "location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_victims",
            "description": "Search the victim manifest to find people by location or name. Use this when asked 'who is in Sector X' or 'have we found person Y'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Search by location (e.g. 'Sector 3')."},
                    "name": {"type": "string", "description": "Search by victim name."}
                },
                "required": []
            }
        }
    }
]
