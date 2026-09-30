import json
from integration.bridge import Bridge
PLUGIN = {
    'name': 'ultron_capability',
    'description': 'Yerel/offline düşünme, kod yazma/analiz, planlama ve uzun agent görevleri için birleşik ULTRON motoru. Normal ses, tarayıcı ve masaüstü işlemlerinde mevcut MARK araçlarını kullan. Onay veremez; onay isteyen görevleri kullanıcıya bildir.',
    'parameters': {'type': 'OBJECT', 'properties': {
        'text': {'type': 'STRING', 'description': 'İstek'},
        'mode': {'type': 'STRING', 'enum': ['auto', 'coding', 'fast', 'general', 'agent']}
    }, 'required': ['text']},
}

def run(parameters, player=None, session_memory=None):
    try:
        result = Bridge().ask(parameters['text'], parameters.get('mode', 'auto'))
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return f'Yerel motor kullanılamıyor: {exc}'
