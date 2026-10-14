from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import coding_bench


class CodingBenchmarkContracts(unittest.TestCase):
    def test_registry_covers_eight_distinct_coding_tasks(self):
        self.assertEqual(len(coding_bench.TASKS), 8)
        self.assertEqual({task["category"] for task in coding_bench.TASKS}, coding_bench.CATEGORIES)
        self.assertTrue(any(task["language"] == "typescript" for task in coding_bench.TASKS))
        self.assertTrue(any(len(task["starter_files"]) > 1 for task in coding_bench.TASKS))

    def test_model_prompt_contains_task_and_starters_but_not_hidden_oracles(self):
        task = coding_bench.TASKS[0]
        prompt = coding_bench.build_prompt(task)
        self.assertIn(task["prompt"], prompt)
        parsed = json.loads(prompt)
        for path, content in task["starter_files"].items():
            self.assertIn(path, [entry["path"] for entry in parsed["working_files"]])
            self.assertIn(content, [entry["content"] for entry in parsed["working_files"]])
        self.assertNotIn("hidden_test", prompt)
        self.assertNotIn("oracle", prompt.lower())
        self.assertNotIn(task["oracle_script"], prompt)

    def test_patch_path_scope_is_exact_and_rejects_traversal(self):
        task = coding_bench.TASKS[0]
        valid = {"files": [{"path": "solution.py", "content": "def normalize_key(value): return value.lower()\n"}]}
        self.assertEqual(coding_bench.validate_patch(task, valid)[0][0], "solution.py")
        for path in ("../solution.py", "/tmp/solution.py", "secret.txt"):
            bad = {"files": [{"path": path, "content": "x"}]}
            with self.subTest(path=path), self.assertRaises(coding_bench.BenchmarkError):
                coding_bench.validate_patch(task, bad)

    def test_dry_run_reports_all_model_quality_as_not_run(self):
        report = coding_bench.run_benchmark(provider=None)
        self.assertEqual(report["model_status"], "NOT_RUN")
        self.assertEqual(report["summary"]["not_run"], 8)
        self.assertEqual(report["summary"]["pass"], 0)
        self.assertTrue(all(row["status"] == "NOT_RUN" for row in report["tasks"]))

    def test_fake_python_model_is_scored_only_by_hidden_pytest_oracle(self):
        task = coding_bench.TASKS[0]
        response = json.dumps({"summary": "Normalize the key", "files": [{
            "path": "solution.py",
            "content": "def normalize_key(value: str) -> str:\n    return value.strip().casefold()\n",
        }]})
        with patch.object(coding_bench, "infer_with_budget", return_value=response) as model:
            result = coding_bench.run_task(task, provider="ollama", infer_fn=model)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["attempts"], 1)
        self.assertGreaterEqual(result["elapsed_ms"], 0)
        sent_prompt = model.call_args.args[0]
        self.assertNotIn(task["oracle_script"], sent_prompt)

    def test_registered_oracles_reproduce_each_starter_defect_without_a_provider(self):
        tsc = coding_bench.ROOT / "ultron/frontend/node_modules/.bin/tsc"
        results = []
        for task in coding_bench.TASKS:
            if task["language"] == "typescript" and not tsc.is_file():
                continue
            with self.subTest(task=task["id"]), tempfile.TemporaryDirectory() as task_tmp, \
                 tempfile.TemporaryDirectory() as oracle_tmp:
                workspace = Path(task_tmp)
                for rel, content in task["starter_files"].items():
                    target = workspace / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding="utf-8")
                passed, _, _ = coding_bench._run_oracle(
                    task, workspace, Path(oracle_tmp), typescript_bin=tsc,
                    node_bin="node")
                results.append((task["id"], passed))
        self.assertGreaterEqual(len(results), 7)
        self.assertEqual([task_id for task_id, passed in results if passed], [])

    def test_one_failed_hidden_test_allows_only_one_repair(self):
        task = coding_bench.TASKS[0]
        responses = [
            json.dumps({"files": [{"path": "solution.py", "content": "def normalize_key(value): return value.strip()\n"}]}),
            json.dumps({"files": [{"path": "solution.py", "content": "def normalize_key(value): return value.strip().casefold()\n"}]}),
        ]
        with patch.object(coding_bench, "infer_with_budget", side_effect=responses) as model:
            result = coding_bench.run_task(task, provider="ollama", infer_fn=model)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(model.call_count, 2)

    def test_typescript_task_uses_compiler_and_hidden_runtime_oracle_when_installed(self):
        task = next(task for task in coding_bench.TASKS if task["language"] == "typescript")
        tsc = coding_bench.ROOT / "ultron/frontend/node_modules/.bin/tsc"
        if not tsc.is_file() or not shutil.which("node"):
            self.skipTest("TypeScript toolchain is not installed in this environment")
        response = json.dumps({"files": [{"path": "formatCompactCount.ts", "content": (
            "export function formatCompactCount(value: number): string {\n"
            "  if (!Number.isFinite(value)) return '';\n"
            "  const sign = value < 0 ? '-' : '';\n"
            "  const n = Math.abs(value);\n"
            "  if (n < 1000) return String(value);\n"
            "  if (n < 1000000) return sign + (n / 1000).toFixed(1) + 'K';\n"
            "  return sign + (n / 1000000).toFixed(1) + 'M';\n}\n"
        )}]})
        with patch.object(coding_bench, "infer_with_budget", return_value=response):
            result = coding_bench.run_task(task, provider="ollama", typescript_bin=tsc)
        self.assertEqual(result["status"], "PASS", result)

    def test_cloud_requires_explicit_budget_and_call_ceiling_before_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.json"
            with patch.dict("os.environ", {
                "GOLGE_AUTODEV_GEMINI_API_KEY": "test-only",
                "GOLGE_AUTODEV_CLOUD_MODEL_BUDGET_APPROVED": "false",
                "GOLGE_AUTODEV_MAX_COST_USD": "0",
            }):
                report = coding_bench.run_benchmark(provider="gemini", max_cases=1,
                                                    cloud_budget_confirmed=False)
            self.assertEqual(report["model_status"], "BLOCKED")
            self.assertEqual(report["summary"]["blocked"], 1)

    def test_provider_outage_is_probed_once_then_remaining_tasks_are_not_run(self):
        def unavailable(*_args):
            raise ConnectionError("provider offline")
        with patch.object(coding_bench, "infer_with_budget", side_effect=unavailable) as model:
            report = coding_bench.run_benchmark(provider="ollama", max_cases=8, max_calls=8)
        self.assertEqual(model.call_count, 1)
        self.assertEqual(report["tasks"][0]["status"], "NOT_RUN")
        self.assertTrue(all(row["status"] == "NOT_RUN" for row in report["tasks"]))
        self.assertEqual(sum(row["provider_calls"] for row in report["tasks"]), 1)


if __name__ == "__main__":
    unittest.main()
