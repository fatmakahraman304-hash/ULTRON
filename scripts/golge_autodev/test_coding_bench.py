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
    def test_v7_local_benchmark_requests_structured_json_without_oracle_data(self):
        prompt = coding_bench.build_prompt(coding_bench.TASKS[0])
        with patch("engine.infer", return_value='{"files": []}') as local:
            result = coding_bench.infer_with_budget(prompt, "ollama")
        self.assertEqual(result, '{"files": []}')
        self.assertEqual(local.call_args.kwargs["max_output_tokens"], coding_bench.MAX_OUTPUT_TOKENS)
        schema = local.call_args.kwargs["response_schema"]
        self.assertEqual(schema["type"], "object")
        self.assertIn("files", schema["required"])
        self.assertEqual(schema["properties"]["files"]["type"], "array")
        self.assertNotIn(coding_bench.TASKS[0]["oracle_script"], json.dumps(schema))
        with patch("engine.infer", return_value="{}") as cloud:
            coding_bench.infer_with_budget(prompt, "gemini")
        self.assertNotIn("response_schema", cloud.call_args.kwargs)

    def test_v7_local_schema_does_not_replace_allowlist_or_secret_gates(self):
        task = coding_bench.TASKS[0]
        schema = coding_bench.LOCAL_PATCH_RESPONSE_SCHEMA
        self.assertTrue(schema["properties"]["files"]["items"]["additionalProperties"] is False)
        with self.assertRaisesRegex(coding_bench.BenchmarkError, "model_path_outside_task"):
            coding_bench.validate_patch(task, {"files": [
                {"path": "../private.py", "content": "pass"}
            ]})
        with self.assertRaisesRegex(coding_bench.BenchmarkError, "model_patch_incomplete"):
            coding_bench.validate_patch(task, {"files": []})


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


    def test_v6_generic_coding_rules_do_not_reveal_hidden_oracle(self):
        task = coding_bench.TASKS[0]
        rendered = coding_bench.build_prompt(task)
        payload = json.loads(rendered)
        self.assertTrue(payload["coding_rules"])
        self.assertIn("raw inputs", rendered)
        self.assertNotIn(task["oracle_script"], rendered)
        self.assertNotIn("oracle", rendered.lower())

    def test_v6_malformed_json_can_recover_once_without_changing_oracle(self):
        task = coding_bench.TASKS[0]
        valid = json.dumps({"files": [{"path": "solution.py",
                           "content": "def normalize_key(value): return value.strip().casefold()\n"}]})
        with patch.object(coding_bench, "_run_oracle",
                          side_effect=[(False, "baseline failed", 1), (True, "PASS", 1)]) as oracle, \
             patch.object(coding_bench, "infer_with_budget", side_effect=["invalid JSON", valid]) as model:
            result = coding_bench.run_task(task, provider="ollama", infer_fn=model)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["provider_calls"], 2)
        self.assertEqual(oracle.call_count, 2)
        prompt = model.call_args_list[1].args[0]
        self.assertIn("model_json_invalid", prompt)
        self.assertNotIn(task["oracle_script"], prompt)

    def test_v6_incomplete_file_list_retries_then_passes(self):
        task = coding_bench.TASKS[0]
        valid = json.dumps({"files": [{"path": "solution.py",
                           "content": "def normalize_key(value): return value.strip().casefold()\n"}]})
        with patch.object(coding_bench, "_run_oracle",
                          side_effect=[(False, "baseline failed", 1), (True, "PASS", 1)]), \
             patch.object(coding_bench, "infer_with_budget",
                          side_effect=[json.dumps({"files": []}), valid]) as model:
            result = coding_bench.run_task(task, provider="ollama", infer_fn=model)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(model.call_count, 2)
        self.assertIn("model_patch_incomplete", model.call_args_list[1].args[0])

    def test_v6_malformed_json_still_blocks_after_two_attempts(self):
        task = coding_bench.TASKS[0]
        with patch.object(coding_bench, "_run_oracle",
                          return_value=(False, "baseline failed", 1)) as oracle, \
             patch.object(coding_bench, "infer_with_budget",
                          side_effect=["not json", "still not json"]) as model:
            result = coding_bench.run_task(task, provider="ollama", infer_fn=model)
        self.assertEqual(result["status"], "BLOCKED", result)
        self.assertEqual(result["reason"], "model_json_invalid")
        self.assertEqual(model.call_count, 2)
        self.assertEqual(oracle.call_count, 1)

    def test_v6_unsafe_paths_fail_closed_without_retry(self):
        task = coding_bench.TASKS[0]
        unsafe = json.dumps({"files": [{"path": "../escape.py", "content": "pass"}]})
        with patch.object(coding_bench, "_run_oracle",
                          return_value=(False, "baseline failed", 1)) as oracle, \
             patch.object(coding_bench, "infer_with_budget", return_value=unsafe) as model:
            result = coding_bench.run_task(task, provider="ollama", infer_fn=model)
        self.assertEqual(result["status"], "BLOCKED", result)
        self.assertEqual(result["reason"], "model_path_outside_task")
        self.assertEqual(model.call_count, 1)
        self.assertEqual(oracle.call_count, 1)

    def test_v6_unchanged_repair_cannot_retest_identical_failed_code(self):
        task = coding_bench.TASKS[0]
        repeated = json.dumps({"files": [{"path": "solution.py",
                              "content": "def normalize_key(value): return value.strip()\n"}]})
        with patch.object(coding_bench, "_run_oracle",
                          side_effect=[(False, "baseline failed", 1),
                                       (False, "observed test failure", 1)]) as oracle, \
             patch.object(coding_bench, "infer_with_budget",
                          side_effect=[repeated, repeated]) as model:
            result = coding_bench.run_task(task, provider="ollama", infer_fn=model)
        self.assertEqual(result["status"], "FAIL", result)
        self.assertEqual(result["reason"], "unchanged_patch_after_repair")
        self.assertEqual(result["provider_calls"], 2)
        self.assertEqual(model.call_count, 2)
        self.assertEqual(oracle.call_count, 2)
        self.assertIn("public_repair_feedback", model.call_args_list[1].args[0])
        self.assertNotIn("observed test failure", model.call_args_list[1].args[0])


    def test_v7_hidden_oracle_output_never_reaches_model_or_report(self):
        task = coding_bench.TASKS[0]
        secret = "PRIVATE_ACCEPTANCE_EXPECTED_8392"
        first = json.dumps({"files": [{"path": "solution.py",
                           "content": "def normalize_key(value): return value.strip()\n"}]})
        second = json.dumps({"files": [{"path": "solution.py",
                            "content": "def normalize_key(value): return value.lower()\n"}]})
        with patch.object(coding_bench, "_run_oracle",
                          side_effect=[(False, "baseline", 1),
                                       (False, f"AssertionError: {secret}", 1),
                                       (False, f"AssertionError: {secret}", 1)]) as oracle, \
             patch.object(coding_bench, "infer_with_budget",
                          side_effect=[first, second]) as model:
            result = coding_bench.run_task(task, provider="ollama", infer_fn=model)
        self.assertEqual(result["status"], "FAIL", result)
        self.assertEqual(oracle.call_count, 3)
        self.assertIn("public_repair_feedback", model.call_args_list[1].args[0])
        self.assertNotIn(secret, model.call_args_list[1].args[0])
        self.assertNotIn(secret, json.dumps(result))
        self.assertIn("repair_feedback", result)

    def test_v7_python_cosmetic_repair_does_not_rerun_hidden_checks(self):
        task = coding_bench.TASKS[0]
        first = json.dumps({"files": [{"path": "solution.py",
                           "content": "def normalize_key(value): return value.strip()\n"}]})
        second = json.dumps({"files": [{"path": "solution.py",
                            "content": "# no behavioral change\ndef normalize_key(value):\n    return value.strip()\n"}]})
        with patch.object(coding_bench, "_run_oracle",
                          side_effect=[(False, "baseline", 1),
                                       (False, "hidden check failed", 1)]) as oracle, \
             patch.object(coding_bench, "infer_with_budget",
                          side_effect=[first, second]) as model:
            result = coding_bench.run_task(task, provider="ollama", infer_fn=model)
        self.assertEqual(result["status"], "FAIL", result)
        self.assertEqual(result["reason"], "structurally_unchanged_patch_after_repair")
        self.assertEqual(model.call_count, 2)
        self.assertEqual(oracle.call_count, 2)

    def test_v7_public_source_feedback_detects_signature_and_syntax(self):
        task = {"starter_files": {"solution.py": "def f(x):\n    return x\n"}}
        changed_signature = coding_bench._public_repair_feedback(
            task, {"solution.py": "def f(y):\n    return y\n"})
        self.assertIn("original public signature", changed_signature)
        syntax_error = coding_bench._public_repair_feedback(
            task, {"solution.py": "def f(:\n    return x\n"})
        self.assertIn("Candidate syntax error", syntax_error)
        self.assertNotIn("AssertionError", syntax_error)

    def test_v7_ast_unchanged_guard_keeps_meaningful_changes_and_ts(self):
        self.assertFalse(coding_bench._same_python_structure(
            {"solution.py": "def f(x): return x\n"},
            [("solution.py", "def f(x): return x + 1\n")]))
        self.assertFalse(coding_bench._same_python_structure(
            {"file.ts": "const value = 1;"},
            [("file.ts", "const value = 1;")]))


    def test_v7_repair_prompt_explains_source_delta_without_private_oracles(self):
        task = {
            "prompt": "Make transform preserve valid IDs, reject empty values, and trim input.",
            "starter_files": {"module.py": "def transform(value):\n    return value\n"},
            "oracle_script": "TOP_PRIVATE_ASSERTION_4125",
        }
        current = {"module.py": "def transform(value):\n    return value.strip()\n"}
        initial = json.loads(coding_bench.build_prompt(task, current_files=current))
        self.assertNotIn("repair_rules", initial)
        repaired = json.loads(coding_bench.build_prompt(
            task, current_files=current, diagnostics="Independent behavior failed",
            repair_mode=True,
        ))
        self.assertIn("return value.strip()", repaired["working_files"][0]["content"])
        delta = repaired["public_candidate_vs_starter_diff"]
        self.assertIn("starter/module.py", delta)
        self.assertIn("candidate/module.py", delta)
        self.assertIn("-    return value", delta)
        self.assertIn("+    return value.strip()", delta)
        self.assertTrue(any("behavior-changing" in rule for rule in repaired["repair_rules"]))
        self.assertNotIn("TOP_PRIVATE_ASSERTION_4125", json.dumps(repaired))

    def test_v7_second_model_attempt_uses_only_public_source_for_repair(self):
        task = {
            "id": "synthetic-repair",
            "category": "python_bugfix",
            "prompt": "Implement compute so the result is transformed as specified.",
            "language": "python",
            "starter_files": {"compute.py": "def compute(value):\n    return value\n"},
        }
        candidate = "def compute(value):\n    return value + 1\n"
        repair = "def compute(value):\n    return value + 2\n"
        responses = [
            json.dumps({"files": [{"path": "compute.py", "content": candidate}]}),
            json.dumps({"files": [{"path": "compute.py", "content": repair}]}),
        ]
        private = "WITHHELD_RESULT_7831"
        with patch.object(coding_bench, "_run_oracle", side_effect=[
            (False, "baseline failure", 1),
            (False, private, 1),
            (True, "pass", 1),
        ]) as oracle, patch.object(coding_bench, "infer_with_budget", side_effect=responses) as model:
            result = coding_bench.run_task(task, provider="ollama", infer_fn=model)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["provider_calls"], 2)
        self.assertEqual(oracle.call_count, 3)
        prompts = [json.loads(call.args[0]) for call in model.call_args_list]
        self.assertNotIn("repair_rules", prompts[0])
        self.assertIn("repair_rules", prompts[1])
        self.assertIn("+    return value + 1", prompts[1]["public_candidate_vs_starter_diff"])
        self.assertNotIn(private, json.dumps(prompts))
        self.assertNotIn(private, json.dumps(result))

    def test_v7_public_source_diff_is_bounded_for_large_changes(self):
        task = {
            "starter_files": {"large.py": "def f():\n    return 0\n"},
            "oracle_script": "FORBIDDEN_PRIVATE_TEST_9901",
        }
        candidate = {"large.py": "def f():\n    return 1\n" + ("# long unrelated comment\n" * 20_000)}
        delta = coding_bench._public_candidate_delta(task, candidate)
        self.assertLessEqual(len(delta), 2_800)
        self.assertNotIn(task["oracle_script"], delta)




if __name__ == "__main__":
    unittest.main()
