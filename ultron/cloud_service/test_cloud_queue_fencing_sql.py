"""Regression assertions for Cloud queue fencing guards."""
import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).with_name('app.py')

class CloudQueueFencingSQLTests(unittest.TestCase):
    def test_fencing_guards_present(self):
        tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
        functions = {node.name: node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)}
        for name in ('complete_device_command', 'append_device_command_progress', 'save_device_command_checkpoint'):
            self.assertIn(name, functions)
            sql = '\n'.join(node.value for node in ast.walk(functions[name]) if isinstance(node, ast.Constant) and isinstance(node.value, str))
            self.assertIn('delivery_attempt', sql)
            self.assertIn("status='delivered'", sql)

if __name__ == '__main__':
    unittest.main()
