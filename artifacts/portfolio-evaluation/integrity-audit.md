# Portfolio evaluation integrity audit

PASS. Read-only audit of the completed 20-case model run; no model requests,
source changes, artifact changes, or test runs were performed for this audit.

- All 20 case IDs occur exactly once in frozen task order. The six original
  journal records remain an exact 28,694-byte prefix; resumed requests cover only
  cases 07–20. Prefix SHA-256:
  `1463203a1aef34bd1054852bc5d1af4f43d1a99c668494b86c8f9218721d095e`.
- Every response outcome equals its final parsed attempt. Every saved raw
  prediction matches the original first output, every final prediction matches
  the accepted outcome, and all nine blocked responses have no accepted outcome.
  All cases have backend `model`, execution disabled, and no tool result.
- Recomputing both reports with the original canonical evaluator exactly matches
  every saved scoring field. Raw first attempt: strict 7/20, outcome 12/20,
  valid 15/20. Guarded final decision: strict 3/20, outcome 7/20, valid 11/20.
  The final guard reduced strict success on this holdout; these results do not
  demonstrate a quality improvement.
- All 22 frozen source/config/schema SHA-256 hashes still match. The original
  evaluation script remains
  `b24de42e11c533712d33c2eec2f4a717fdca0faa4bdca28608ccee8c9994441d`.
  Current and frozen data match
  `41bc632a179f769c0b9080f6a54c0952e148cb359cba1885cf263a3dfab80510`;
  both dataset manifests match
  `1f8023200297080456d9ebdf96b6c9b49b1b55e516a7009bb024cd0980c82a1f`.
- All 20 full model metadata objects are identical, including original versus
  resumed cases: pinned Qwen revision/weights, greedy decoding, full generation
  configuration, seed 42, CPU float32, four intra-operation threads and one
  inter-operation thread. Installed library versions match the frozen protocol.
- The completed run records 20 first attempts and five bounded repair attempts,
  with zero operational error cases. Rules-baseline results are separate and
  must not be described as LLM accuracy. Execution safety is not measured by this
  decision-only run.
- Resume provenance records PID 31604, UTC start
  `2026-11-09T02:38:52.161680+00:00`, UTC completion
  `2026-11-09T02:49:13.686954+00:00`, the preserved prefix hash, and the separate
  resume script hash. Original worker PID/start/stop times were not retained.
  Reported **804.4412896200074 seconds** is the sum of saved per-case response
  runtimes across both processes. It excludes the idle interruption and is not
  continuous elapsed wall time. Resumed-process active wall time is separately
  recorded as 621.524956553003 seconds.

Protocol SHA-256:
`3cd59ee03235186bd66d6a824e567466d777d497250da6b70138003c5f24075e`.
Final journal SHA-256:
`f7ba5a3c8a263d6f7cd17976e33d47625d88ed1b354e4c098f0fa19e8b99fe15`.
Resume script SHA-256:
`1b1dd7b573ae8d538569d2f45f5770df7373380da9c8493f3cf716d6b360c7aa`.
