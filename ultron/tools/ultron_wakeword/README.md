# ULTRON Wake-Word Training Kit

Goal: produce a real OpenWakeWord model for the phrase `ULTRON`.

## Important
- `hey_jarvis` is only an inference test and is not renamed into an ULTRON model.
- The included training config is a template for the OpenWakeWord training notebook/pipeline.
- The final artifact expected by ULTRON is `ultron.onnx`.

## Colab
Use the OpenWakeWord custom-model training notebook. Set the target word/phrase to `ULTRON` and the model name to `ultron`. The notebook can generate synthetic positives and adversarial negatives, augment them, train, and export ONNX.

## Windows install
After obtaining `ultron.onnx`, copy it to:
`backend/data/voice/wake/ultron.onnx`

The runtime prefers a model whose filename stem is `ultron`, so a leftover `hey_jarvis` model cannot silently become the active model.

## Quick test
Run from the project root:
`\.venv\Scripts\python.exe scripts\test_ultron_wakeword.py`
