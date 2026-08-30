# Nolane Plan

**Strategic Future-Space Runtime for AI Agents — v0.15 reference implementation line**

Nolane Plan treats planning as compilation of a bounded strategic future space rather than a longer checklist or a plan→execute→replan wrapper. The runtime keeps canonical state, future families, obligations, uncertainty, principal-relative information, proof dependencies, contingent policy, temporal/resource constraints and execution authority outside model narration and makes correctness-significant shortcuts executable and replayable.

This repository is a **model-free, standard-library-first reference runtime** derived from the Nolane Plan v0.15 architecture specification.

## Runtime line

`0.6.0a1` is the Wave-6 schedulability/liveness and future-temporal-resource closure line.

It preserves one serialized correctness writer and extends the Wave-5 sealed-policy authority path with:

- revisioned control-plane resource and reaction-job contracts;
- joint reaction schedulability certificates rather than per-reaction latency optimism;
- protected deadline-critical planning capacity;
- repeated `SAFE_HANDOFF` liveness/progress certificates with grounded deadlines and bounded stutter;
- activation-time handoff stability and refresh semantics;
- transition/observation-model adequacy kept distinct from policy totality;
- declared-failure-set-relative option independence and robust preparedness;
- strong dormant-branch resurrection revalidation;
- Wave-6 authority prerequisites that still delegate to existing sealed-policy → proof → identity authority;
- snapshot-v6 persistence/replay with canonical internal digest checks and bounded v5 migration;
- exact 43-case v0.6 failure-taxonomy conformance and a 12-mutant constitutional gate.

Wave 6 deliberately does **not** claim distributed correctness writers, generic scheduling/orchestration, complete global migration/replay exhaustion, production hardening, formal global correctness or empirical superiority.

## Core architecture

```text
                     speculative/model workers
                   /          |            \
           principal A    principal B    verifier
                   \          |            /
                    +----------------------+
                               |
                      serialized PlanKernel
                               |
          +--------------------+--------------------+
          |                    |                    |
    canonical state     evidence / proof      trust / identity
          |                    |                    |
          +------------- Decision Cut --------------+
                               |
                 principal-scoped DecisionEpoch
                               |
                   information partition/frontier
                               |
                   sealed contingent policy IR
                               |
                    frozen advisory selection
                               |
          sufficiency + PlanSeal + executability
                               |
        schedulability + liveness + edge stability
             + adequacy + option independence
                               |
                 proof-carrying authorization
                               |
               principal/adapter dispatch fence
                               |
                         external effect
                               |
              verify / reconcile ambiguous outcome
                               |
                        canonical commit
```

## Constitutional properties

The bounded reference runtime currently enforces, among others:

- canonical state outranks model narrative;
- mission revisions invalidate stale completion and decision artifacts;
- `NULL_WORLD` / residual unknown-world state remains explicit;
- principal identity is host/platform-grounded and distinct from role/model/session/grant;
- kernel-global visibility does not imply principal-available knowledge;
- Decision Capsules are recipient-, information-scope- and causal-cut-bound;
- historical Decision Cuts do not see future artifacts retroactively;
- proof artifacts bind captured inputs, query-domain membership/result sensitivity and semantic/trust/execution profiles;
- blocking invalidity cannot be replaced by “absence of a blocker” or positive support alone;
- contingent policy splits obey principal-relative non-anticipativity;
- `SelectionRecord` is advisory; hard vetoes cannot be resurrected by score;
- PlanSeal assurance cannot self-promote and invalidated seals cannot revive;
- recursive recall compares downstream decision signatures;
- totality requires supported outcomes to have valid handlers and remains distinct from open-world model adequacy;
- IA1 possible timing is not promoted to an IA2 bounded reaction guarantee;
- local reaction feasibility does not imply joint policy schedulability;
- verifier/model/rate-limit/human/kernel-writer resources can participate in reaction feasibility;
- speculative planning cannot consume protected capacity reserved for imminent correctness-critical reaction work;
- repeated `SAFE_HANDOFF` cannot indefinitely rename, defer or self-extend required continuation work;
- executable-horizon advance cannot launder new critical debt or synthesis-workload regression;
- a valid policy edge does not waive activation-time generation, permission, reservation, writer or open-side-effect refresh;
- fallback count does not create robustness when routes share a declared common-mode dependency;
- dormant protected branches cannot resurrect without current revalidation of their bound semantic dimensions;
- Wave-6 objects add prerequisites but do not mint an independent authority path;
- dispatch remains durably recorded before side effects;
- ambiguous non-idempotent outcomes require evidence-bound reconciliation;
- snapshot restore verifies outer integrity, hash-chain/prefix binding and layer-internal canonical digests;
- stale resource/policy/proof/trust state does not silently resurrect after restart;
- correctness-significant mutation remains under one serialized writer.

## Quick start

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m nolane_plan conformance
python -m nolane_plan.wave2_conformance
python -m nolane_plan.wave3_conformance
python scripts/wave3_mutation_gate.py
python -m nolane_plan.wave4_conformance
python scripts/wave4_mutation_gate.py
python -m nolane_plan.wave5_conformance
python scripts/wave5_mutation_gate.py
python -m nolane_plan.wave6_conformance
python scripts/wave6_mutation_gate.py
python -m nolane_plan demo --root .demo-plan
```

Resume a saved runtime:

```python
from nolane_plan import PlanKernel

kernel = PlanKernel.open(".demo-plan")
```

`PlanKernel.open()` is a correctness operation, not a permissive loader. Unknown correctness-significant replay events fail closed instead of being guessed.

## Current deterministic gates

| Surface | Result |
|---|---:|
| Principal-scope projection oracle | v0.14 `108` collisions → v0.15 `0` |
| Wave 2 adversarial conformance | 10/10 |
| Wave 3 adversarial / mutations | 12/12 + 4/4 |
| Wave 4 adversarial / mutations | 14/14 + 7/7 |
| Wave 5 adversarial / mutations | 29/29 + 13/13 |
| Wave 6 exact failure taxonomy / mutations | 43/43 + 12/12 |
| Unit/integration suite | 334/334 |
| Python release matrix | 3.11 / 3.12 / 3.13 |

The Wave-6 release gate also requires source compilation and the end-to-end demo on each matrix entry. See `CONFORMANCE.md` for the exact claim boundary.

## Package map

| Module | Responsibility |
|---|---|
| `kernel` | serialized correctness writer and end-to-end lifecycle |
| `decision_cut` / `artifacts` | causal-cut authority and artifact freshness |
| `trust_runtime` / `trust_recovery` | host-grounded identity, communication, execution evidence and replay |
| `proof_runtime` / `proof_recovery` | proof dependency/support authority and replay |
| `policy_information` / `policy_ir` | principal-scoped information and contingent policy graph |
| `selection` | frozen advisory selection transactions/records |
| `seals` / `seal_lifecycle` | decision sufficiency, proof-context composition and PlanSeal lifecycle |
| `policy_certificates` | recursive recall, totality and policy-edge stitch certificates |
| `policy_readiness` / `policy_executability` | reaction/readiness, continuation and exact-scope `EXEC_*` assessment |
| `policy_runtime` / `policy_recovery` | sealed-policy authority and snapshot-v5 layer |
| `control_plane` / `schedulability` | revisioned resources/jobs and joint reaction schedulability |
| `handoff_liveness` | bounded progress/stutter and grounded deadline semantics |
| `handoff_stability` | activation-time child-entry freshness/refresh contracts |
| `policy_coverage` | modeled totality vs transition/observation adequacy and residual status |
| `option_independence` | common-mode-aware route independence and robust preparedness |
| `future_resurrection` | revisioned dormancy/resurrection revalidation |
| `schedulability_runtime` | Wave-6 kernel prerequisites under the canonical writer |
| `schedulability_codec` / `schedulability_recovery` | snapshot-v6 canonical persistence and replay |
| `execution` | adapter capability profiles and durable action transactions |
| `future` / `compiler` | future families, `NULL_WORLD`, strategic lattice and bounded compilation |
| `obligations` | condition-centric strategic obligations |
| `budget` / `resources` | protected planning capacity and shared commitments |
| `persistence` / `resume` | journal/snapshot integrity and lower-layer replay |
| `conformance`, `wave2_conformance` … `wave6_conformance` | bounded executable falsification suites |

## Research and engineering boundary

This repository is a reference implementation, not evidence that Nolane Plan is empirically superior to existing planners, POMDP systems, HTN planners, MCTS systems or production agent frameworks. Passing bounded conformance and mutation gates means specific encoded shortcuts were rejected at the tested scope; it is not a global formal proof.

The next engineering closure is Wave 7: common durable lineage, broader schema/world/environment versioning, replay/migration exhaustion and compaction lineage. Wave 8 then targets property/metamorphic/chaos/differential conformance and final spec-to-code exhaustion. Empirical benchmark superiority remains a measurement question, not a correctness claim.
