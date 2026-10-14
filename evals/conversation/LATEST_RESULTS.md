## 2026-10-14 — Intent routing v2 (deterministic only)

The new `intent_scenarios.json` suite has 100 distinct one-turn routing cases,
ten categories, five Turkish and five English cases per category. `intent_eval.py`
reports **100/100** for the deterministic intent, context-required and tool-required
labels. The production `b6b563d` dialogue-act classifier matched **32/100** on
these expanded labels. A repeated in-process benchmark measured old route p50/p95
at **0.003164/0.004637 ms** and new route p50/p95 at **0.038924/0.080290 ms**;
no model calls were added. This measures lexical code only and is not a model
quality result or first-token/total-response latency measurement.

Intent-suite SHA256: `e640562e2011e9189471182f570511b5e9181c7e553e59914170db23cb8c8ef4`.

The separate real-answer suite `scenarios.json` still has **100/100 NOT_RUN** for
Gemini and Qwen: this environment has no `GEMINI_API_KEY` and no reachable local
Ollama. No transcripts or model scores were fabricated. First-token and total
model latency remain **NOT_RUN**.

# Verified evaluation status — 2026-10-10

Suite SHA256: `e59d9af95f1b891e969afa9c3550ca069b13aa5226246c251bc9eae9931f7d26`

**Live conversational quality: NOT MEASURED. 100/100 has not been reached or claimed.**

Both real-provider commands were attempted. Gemini could not start because this
execution environment has no configured GEMINI_API_KEY. Qwen could not start
because there is no reachable local Ollama server. No credentials were extracted
from Render and no Windows installation/model download was attempted.

Each provider report contains 100 NOT_RUN scenarios, zero captured transcripts,
no independent reviews and a null model-quality score. NOT_RUN is not a measured
model failure. Infrastructure validation is separate from answer quality.

| Category | Scenarios | Gemini | Qwen |
| --- | ---: | --- | --- |
| daily | 10 | NOT_RUN | NOT_RUN |
| context | 10 | NOT_RUN | NOT_RUN |
| switch | 10 | NOT_RUN | NOT_RUN |
| recall | 10 | NOT_RUN | NOT_RUN |
| persona | 10 | NOT_RUN | NOT_RUN |
| length | 10 | NOT_RUN | NOT_RUN |
| humour | 10 | NOT_RUN | NOT_RUN |
| correction | 10 | NOT_RUN | NOT_RUN |
| reasoning | 10 | NOT_RUN | NOT_RUN |
| safety | 10 | NOT_RUN | NOT_RUN |

Deterministic verification: 155 Cloud Python tests passed, including 28 real
disposable PostgreSQL tests; 86 mobile Node tests passed; 6 local-brain tests
passed. Frontend TypeScript/Vite build and 6 Earth tests passed. These counts
must never be reported as a conversational quality score. Exact GitHub and Render
release evidence is recorded in ULTRON_TEST_RESULTS.md.

Remaining acceptance requires real model transcripts and independent scoring
under README.md. Measure device latency and actual quantization before choosing
a replacement or larger model. Presentation checks do not prove factual accuracy;
style conflict rules do not resolve arbitrary semantic contradictions.
