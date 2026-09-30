"""Ownership describes dispatch; only MARK can open real-time audio devices."""
OWNERS = {
    'microphone': 'mark', 'speaker': 'mark', 'wake_word': 'mark',
    'conversation': 'mark', 'avatar': 'mark', 'video': 'mark',
    'browser': 'mark', 'computer': 'mark', 'vision': 'mark',
    'memory': 'mark', 'reminders': 'mark', 'telemetry': 'mark',
    'web_search': 'mark', 'planner': 'ultron', 'supervisor': 'ultron',
    'long_tasks': 'ultron', 'local_llm': 'ultron', 'code_intelligence': 'ultron',
    'task_memory': 'ultron', 'task_scheduler': 'ultron',
    'sandbox': 'ultron', 'audit': 'ultron', 'vault': 'ultron',
    'ocr': 'ultron', 'connectors': 'ultron', 'skills': 'ultron',
}
