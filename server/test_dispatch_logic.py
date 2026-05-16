import unittest
from unittest.mock import patch, MagicMock
import tempfile
import sqlite3
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import perform_triage, sanitize_search_query, init_db, update_inventory, consult_protocol, check_inventory
from dispatcher import GemmaDispatcher

class TestCoreLogic(unittest.TestCase):
    """Layer 1: Pure Logic Unit Tests (Fast, Isolated)"""
    
    def test_perform_triage_red_respiration(self):
        # Arrange
        resp_rate = 35
        perfusion = True
        mental_status = True
        
        # Act
        result = perform_triage(resp_rate, perfusion, mental_status)
        
        # Assert
        self.assertIn("RED (Immediate)", result, "High resp rate should trigger RED.")
        
    def test_perform_triage_yellow(self):
        # Arrange
        resp_rate = 20
        perfusion = True
        mental_status = True
        
        # Act
        result = perform_triage(resp_rate, perfusion, mental_status)
        
        # Assert
        self.assertIn("YELLOW (Delayed)", result, "Normal vitals should yield YELLOW.")

    def test_perform_triage_black(self):
        # Arrange
        result = perform_triage(resp_rate=0, perfusion=False, mental_status=False)
        # Assert
        self.assertIn("BLACK (Deceased", result)

    def test_perform_triage_green(self):
        # Arrange
        result = perform_triage(resp_rate=20, perfusion=True, mental_status=True, is_walking=True)
        # Assert
        self.assertIn("GREEN (Minor)", result)

    def test_sanitize_search_query_stopwords(self):
        # Arrange
        search_term = "Environmental damage reported in area"
        
        # Act
        result = sanitize_search_query(search_term)
        
        # Assert
        self.assertNotIn("environmental", [r.lower() for r in result])
        self.assertNotIn("damage", [r.lower() for r in result])
        self.assertIn("area", [r.lower() for r in result])


class TestIntegrationDB(unittest.TestCase):
    """Layer 2: Database Integration Tests with a temporary offline DB"""
    
    def setUp(self):
        """Arrange: Spin up a throwaway SQLite file database so tests don't nuke the real crisis.db"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db_path = self.temp_db.name
        
        # Patch the global DB_PATH in tools so all functions hit this temp file
        self.patcher = patch('tools.DB_PATH', new=self.db_path)
        self.patcher.start()
        
        init_db()

    def tearDown(self):
        self.patcher.stop()
        os.unlink(self.db_path)

    def test_update_inventory_consumption(self):
        # Act: Consume 100 liters
        result = update_inventory("Water", -100)
        
        # Assert
        self.assertIn("400", result, "Inventory should subtract and return the new total correctly.")

    def test_update_inventory_new_item(self):
        # Act: Add a totally new item not in seed
        result = update_inventory("Flashlights", 10)
        
        # Assert
        self.assertIn("Found New Resource", result)
        self.assertIn("10", result)
        
    def test_consult_protocol_fuzzy_match(self):
        # Act
        result = consult_protocol("almond")
        
        # Assert
        self.assertTrue("Found Protocol(s)" in result)
        self.assertTrue("almond" in result.lower() or "cyanide" in result.lower())


class TestAgenticMock(unittest.TestCase):
    """Layer 3: Agentic Routing via Mocking (to avoid spinning up the heavy GPU)"""
    
    @patch('ollama.chat')
    @patch('dispatcher.init_db')
    def test_execute_tool_call(self, mock_init, mock_chat):
        # Arrange: Simulate Ollama returning a tool call
        mock_chat.return_value = {
            "message": {
                "tool_calls": [
                    {
                        "function": {
                            "name": "broadcast_mesh_alert",
                            "arguments": {"message": "Test successful", "priority": "High"}
                        }
                    }
                ]
            }
        }
        
        dispatcher = GemmaDispatcher()
        
        # Act: Single execute() call — no more dual loops
        response_str, ui_alert = dispatcher.execute("Send a mesh alert", [])
        
        # Assert
        self.assertIn("MESH ALERT SENT", response_str)
        self.assertIsNotNone(ui_alert, "UI Alert must be returned for the React frontend.")
        self.assertEqual(ui_alert["title"], "MESH BROADCAST")

    @patch('ollama.chat')
    @patch('dispatcher.init_db')
    def test_execute_text_response(self, mock_init, mock_chat):
        # Arrange: Simulate Ollama returning plain text (no tool call)
        mock_chat.return_value = {
            "message": {
                "content": "All units be advised: situation is stable."
            }
        }
        
        dispatcher = GemmaDispatcher()
        
        # Act
        response_str, ui_alert = dispatcher.execute("Give me a status update", [])
        
        # Assert
        self.assertIn("situation is stable", response_str)
        self.assertIsNone(ui_alert)


if __name__ == '__main__':
    unittest.main()
