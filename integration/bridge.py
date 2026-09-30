import json
import os
from urllib.request import Request, urlopen

class Bridge:
    def __init__(self, url=None, token=None):
        self.url = url or os.environ.get('MARK_ULTRON_URL', '')
        self.token = token or os.environ.get('MARK_ULTRON_TOKEN', '')

    def request(self, path, data=None, timeout=30):
        if not self.url:
            raise RuntimeError('ULTRON servisi hazır değil; START.bat ile başlatın.')
        req = Request(self.url + path,
                      data=json.dumps(data).encode() if data is not None else None,
                      headers={'Content-Type': 'application/json', 'X-MARK-Token': self.token})
        with urlopen(req, timeout=timeout) as response:
            return json.load(response)

    def ask(self, text, mode='auto'):
        return self.request('/api/merged/invoke', {'text': text, 'mode': mode}, timeout=200)

    def health(self):
        return self.request('/api/merged/health', timeout=4)
