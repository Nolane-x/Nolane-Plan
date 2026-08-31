# Nolane Plan

**Strategic Future-Space Runtime for AI Agents — v0.15 reference implementation line**

Nolane Plan treats planning as compilation of a bounded strategic future space rather than a longer checklist or a plan→execute→replan wrapper. Canonical state, evidence, uncertainty, principal-relative information, proof dependencies, contingent policy, temporal/resource constraints, semantic lineage and execution authority remain outside model narration and are made executable, replayable and auditable.

This repository is a **model-free, standard-library-first reference runtime** derived from the Nolane Plan v0.15 architecture specification.

## Runtime line

`0.8.0a1` is the Wave-8 **Conformance Exhaustion** release line.

Wave 8 keeps the Wave-7 single serialized correctness writer and adds a layered falsification surface rather than a second planning/execution stack:

- a frozen registry of exactly **68 invariants**: P01–P10, M01–M12, C01–C10, D01–D10, X01–X12, W01–W06 and S01–S08;
- deterministic bounded case generators and deterministic counterexample minimization;
- property, metamorphic, deterministic-chaos and differential/restart conformance runners;
- durable cancellation-fence semantics: pre-dispatch cancellation is terminal, while post-dispatch cancellation remains `CANCELLATION_PENDING` until evidence-bound reconciliation;
- bounded relocation exhaustion preserving `LOCATED`, `AMBIGUOUS` and `UNLOCATED` instead of collapsing uncertainty;
- repository-owned historical snapshot migration coverage from v2 through v6 into v7 with conservative authority handling;
- bounded finite global-exclusion, N-way context-composition and control-resource monotonicity closure;
- six checked-in reference worlds W01–W06 used as correctness fixtures, not as empirical superiority claims;
- twelve target-specific constitutional mutants X01–X12 with invalid-kill tracking;
- deterministic S01–S08 source/spec coverage reconciliation that keeps PARTIAL, RESEARCH and BOUNDARY claims explicit.

The frozen Wave-8 registry digest is:

`d9f4e9fd9cd111c3a458b2018686060b74235102702352230f7546360a942dfc`

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
       canonical / evidence / trust / proof / policy
                             |
             principal-scoped DecisionEpoch
                             |
            sealed contingent policy + selection
                             |
      sufficiency + schedulability + liveness + lineage
                             |
              proof-carrying authorization
                             |
                 durable dispatch fence
                             |
                    external effect
                             |
          verify / reconcile / cancellation fence
                             |
                   canonical commit
                             |
       journal + snapshot-v7 + fail-closed replay
                             |
       migration + reversible lineage compaction
                             |
        Wave-8 layered falsification / coverage
```

## Constitutional properties

The bounded reference runtime enforces, among others:

- canonical state outranks model narrative;
- host/platform identity cannot be self-asserted by a model;
- kernel-global visibility does not imply principal-available knowledge;
- historical Decision Cuts do not see future artifacts retroactively;
- proof authority binds captured dependencies, query-domain freshness and support/blocker semantics;
- hard selection vetoes cannot be scored back into eligibility;
- non-anticipative policy cannot branch on information unavailable to the acting principal;
- joint resource feasibility is not inferred from per-job feasibility;
- repeated handoff cannot indefinitely rename or defer required continuation work;
- semantic-regime or exact-lineage drift invalidates stale authority before dispatch;
- migration mappings cannot mint or resurrect authorization;
- unknown correctness-significant replay events fail closed;
- representation-only compaction cannot erase protected lineage or strengthen authority;
- cancellation after durable dispatch is not reported as a clean cancellation without reconciliation evidence;
- ambiguous relocation remains ambiguous, and opaque/global theories remain UNKNOWN rather than optimistically composable.

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
python -m nolane_plan.wave7_conformance
python scripts/wave7_mutation_gate.py
python -m nolane_plan.wave8_conformance
python scripts/wave8_mutation_gate.py
python -m nolane_plan.wave8_coverage
python -m nolane_plan demo --root .demo-plan
```

Resume a saved runtime:

```python
from nolane_plan import PlanKernel

kernel = PlanKernel.open(".demo-plan")
```

`PlanKernel.open()` is a correctness operation, not a permissive loader.

## Deterministic release gates

| Surface | Required / verified bounded result |
|---|---:|
| Principal-scope projection oracle | v0.14 `108` collisions → v0.15 `0` |
| Wave 2 adversarial conformance | 10/10 |
| Wave 3 adversarial / mutations | 12/12 + 4/4 |
| Wave 4 adversarial / mutations | 14/14 + 7/7 |
| Wave 5 adversarial / mutations | 29/29 + 13/13 |
| Wave 6 adversarial / mutations | 43/43 + 12/12 |
| Wave 7 adversarial / mutations | 32/32 + 12/12 |
| Wave 8 P/M/C/D/W/S conformance | 10 + 12 + 10 + 10 + 6 + 8, zero counterexamples |
| Wave 8 constitutional mutations | 12/12 killed; 0 invalid kills |
| Wave 8 coverage ledger | 123 rows = 117 in-scope + 1 RESEARCH + 5 BOUNDARY |
| Unit/integration suite | 464/464 at pre-release implementation head |
| Python matrix | 3.11 / 3.12 / 3.13 |

Pre-release implementation head `c75cb337f84a1b0ad0477b2f892723fd8ff672a6` reproduced this surface in CI run `33361860635`. The `0.8.0a1` release candidate must reproduce it at its own exact SHA, then on the pull-request synthetic merge and final `main` before the release is called closed.

## Wave-8 package map

| Module | Responsibility |
|---|---|
| `wave8_registry` | frozen 68-invariant registry and canonical registry digest |
| `wave8_generators` | seeded bounded generators and deterministic minimization |
| `wave8_properties` | P01–P10 property oracles |
| `wave8_metamorphic` | M01–M12 metamorphic relations |
| `wave8_chaos` | C01–C10 deterministic fault schedules |
| `wave8_differential` | D01–D10 live/restart/replay differential relations |
| `wave8_worlds` | W01–W06 bounded correctness worlds and non-gating measurements |
| `wave8_conformance` | unified P/M/C/D/W/S conformance report |
| `wave8_coverage` | S01–S08 final coverage/claim audit |
| `cancellation_runtime` | durable pre/post-dispatch cancellation fence semantics |
| `migration_matrix` | repository-owned historical snapshot migration matrix |

The earlier kernel, trust, proof, policy, schedulability, lineage, migration, replay and compaction modules remain the production semantic surfaces exercised by these falsification layers.

## Research and engineering boundary

`GREEN` means a tested reference implementation for the explicitly bounded scope. It is **not** a formal proof of arbitrary production correctness and is not evidence of empirical superiority over POMDP, HTN, MCTS or other agent/planning systems.

Generalized open/opaque candidate-universe minimality, generalized constraint theories, arbitrary external historical schemas, adapter-specific physical cancellation guarantees, destructive production-storage compaction and distributed/multi-writer consensus remain PARTIAL or BOUNDARY. Benchmark measurements remain RESEARCH and never satisfy a correctness gate.
