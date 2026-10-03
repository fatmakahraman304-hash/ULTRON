"""Validate training inputs without installing packages or pretending a model exists."""
import importlib.util
import json
from pathlib import Path
import sys
import yaml


def check(config_path):
    config_path = Path(config_path).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    base = config_path.parents[2] / "backend"
    missing = []
    positives = {s.casefold().strip() for s in config["target_phrase"]}
    if positives.intersection(s.casefold().strip() for s in config["custom_negative_phrases"]):
        missing.append("Target phrase is also a negative phrase")
    for module in ("torch", "onnx", "torchinfo", "torchmetrics", "audiomentations",
                   "torch_audiomentations", "speechbrain", "pronouncing"):
        if importlib.util.find_spec(module) is None:
            missing.append("Python dependency: " + module)
    def path(value):
        result = Path(value)
        return result if result.is_absolute() else base / result
    if not (path(config["piper_sample_generator_path"]) / "generate_samples.py").is_file():
        missing.append("Piper sample generator source and voice model")
    if not isinstance(config["batch_n_per_class"], dict):
        missing.append("batch_n_per_class must map dataset names to batch sizes")
    for name, filename in config["feature_data_files"].items():
        if not path(filename).is_file():
            missing.append("Negative training features: " + name)
    if not path(config["false_positive_validation_data_path"]).is_file():
        missing.append("Independent false-positive validation features")
    for key in ("rir_paths", "background_paths"):
        if not config[key] or any(not path(v).is_dir() for v in config[key]):
            missing.append("Augmentation audio: " + key)
    return {"ready": not missing, "missing": missing, "model_created": False}


if __name__ == "__main__":
    result = check(Path(__file__).with_name("ultron_training_template.yaml"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["ready"] else 2)
