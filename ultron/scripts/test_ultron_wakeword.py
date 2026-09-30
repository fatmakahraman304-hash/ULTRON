import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
model_dir = root / "backend" / "data" / "voice" / "wake"
models = sorted(list(model_dir.glob("ultron*.onnx")) + list(model_dir.glob("ultron*.tflite")))
print("ULTRON WAKEWORD CHECK")
print("MODEL DIR:", model_dir)
print("ULTRON MODELS:", [p.name for p in models])
if not models:
    print("STATUS: MISSING — place ultron.onnx in backend/data/voice/wake/")
    raise SystemExit(2)
try:
    from openwakeword.model import Model
    m = Model(wakeword_models=[str(models[0])])
    print("STATUS: MODEL LOAD OK")
    print("MODELS:", list(m.models.keys()) if hasattr(m, "models") else "loaded")
except Exception as exc:
    print("STATUS: MODEL LOAD FAILED")
    print(type(exc).__name__ + ":", exc)
    raise SystemExit(1)
