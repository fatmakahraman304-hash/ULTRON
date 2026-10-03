import json
from pathlib import Path
from urllib.request import urlopen
from .paths import ROOT, BACKEND


def download(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.stat().st_size:
        return
    partial = destination.with_suffix(destination.suffix+'.partial')
    with urlopen(url, timeout=90) as response, partial.open('wb') as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    partial.replace(destination)


def main():
    errors = []
    try:
        from core.wake_word import selected_model
        from openwakeword.model import Model
        custom = Path(selected_model())
        if custom.is_file():
            Model(wakeword_models=[str(custom)], inference_framework='onnx')
            print('PASS: custom ULTRON model load')
        else:
            print('WARN: custom ULTRON wake model missing; manual activation available')
    except Exception as exc:
        errors.append('Wake: '+str(exc))
    try:
        from huggingface_hub import snapshot_download
        path = ROOT/'ultron/models/whisper-tiny'
        from faster_whisper import WhisperModel
        try:
            WhisperModel(str(path),device='cpu',compute_type='int8',local_files_only=True)
        except (OSError, RuntimeError, ValueError):
            snapshot_download('Systran/faster-whisper-tiny',local_dir=path,
                allow_patterns=['config.json','model.bin','tokenizer.json','vocabulary.*','preprocessor_config.json'])
            WhisperModel(str(path),device='cpu',compute_type='int8',local_files_only=True)
        print('PASS: Whisper tiny CPU int8 load')
    except Exception as exc:
        errors.append('STT: '+str(exc))
    try:
        model=BACKEND/'data/voice/piper/tr_TR-dfki-medium.onnx'
        base='https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium/'
        for name in (model.name,model.name+'.json'):
            download(base+name,model.parent/name)
        print('PASS: Piper model and metadata downloaded')
    except Exception as exc:
        errors.append('TTS: '+str(exc))
    for error in errors:
        print('WARN:',error)
    return int(bool(errors))

if __name__=='__main__':
    raise SystemExit(main())
