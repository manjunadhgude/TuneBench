# Guard-only comparison

Same Qwen3 GGUF weights, prompt, JSON grammar and CPU settings; the guard changes. All 40 new fictional questions remain in each denominator.

| Version | First correct | Final correct | Correct final tool calls |
| --- | ---: | ---: | ---: |
| v0.5 | 33/40 | 22/40 | 1/16 |
| v0.6 | 33/40 | 22/40 | 1/16 |

Assistant-authored/reviewed synthetic data, not human annotation or a production accuracy estimate. Clarification wording is not human-graded. Execution was disabled. Schema validity is separate from correct decisions. Raw captures, protocols and per-case failures remain beside this report. No labels or outputs were rewritten. This data is now seen and cannot be reused as an unseen test.
