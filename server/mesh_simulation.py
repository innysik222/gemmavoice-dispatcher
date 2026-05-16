import socket
import json
import time

def simulate_mesh_broadcast(message: str, priority: str = "High"):
    """
    Simulates a local UDP broadcast for mesh networking.
    In a real disaster, this would interface with LoRa or Briar.
    """
    UDP_IP = "255.255.255.255"
    UDP_PORT = 5005
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    payload = json.dumps({
        "sender": "GEMMA_RELIEF_UNIT_01",
        "priority": priority,
        "content": message,
        "timestamp": time.time()
    }).encode()
    
    sock.sendto(payload, (UDP_IP, UDP_PORT))
    print(f"MESH BROADCAST [UDP]: {message}")

if __name__ == "__main__":
    simulate_mesh_broadcast("Unit 01 reporting insulin supplies critically low.")
