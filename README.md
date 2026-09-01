# Nolane Plan

**Strategic Future-Space Runtime for AI Agents — v0.15 reference implementation line**

Nolane Plan treats planning as compilation of a bounded strategic future space rather than a longer checklist or a plan→execute→replan wrapper. Canonical state, evidence, uncertainty, principal-relative information, proof dependencies, contingent policy, temporal/resource constraints, semantic lineage and execution authority remain outside model narration and are made executable, replayable and auditable.

This repository is a **model-free, standard-library-first reference runtime** derived from the Nolane Plan v0.15 architecture specification.

## Runtime line

`0.9.0a1` is the Wave-9 **Production Correctness / Distributed Authority** release line.

Wave 9 keeps the established planning, proof, policy, replay, migration and Wave-8 falsification stack and closes three explicitly bounded production surfaces rather than adding a new planner:

- production-store destructive compaction with prepare, shadow verification, durable pointer switch and conservative retirement;
- adapter-bound external execution semantics with exact dispatch, cancellation, fencing, reconciliation and compensation contracts;
- strong multi-writer authority only on storage profiles that actually provide the required durable acknowledgement, exact-revision CAS and fencing semantics.

Restart/replay preserves the new correctness-significant sidecars, stale authority fails closed, and weaker storage or execution backends are not promoted into stronger guarantees. Historical Wave 2–8 gates remain mandatory.

Frozen Wave-9 registry digest: `15e4876c1fabe75bbfe78c5f3a921299315863277bc791ac5324bf6115204ea8`.

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
python -m nolane_plan.wave9_chaos
python -m nolane_plan.wave9_differential
python scripts/wave9_mutation_gate.py
python -m nolane_plan.wave9_coverage
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
| Wave 8 unified conformance / mutations / coverage | GREEN + 12/12 killed, 0 invalid + GREEN |
| Wave 9 registry | 56 invariants; `15e4876c1fabe75bbfe78c5f3a921299315863277bc791ac5324bf6115204ea8` |
| Wave 9 deterministic production-fault schedules | 12/12; `acd59b52184cea99cd5101fde9cb83c74f947b207af813c6ac81388eaf60e01a` |
| Wave 9 differential equivalence | 4/4; `14ab39e4b32a5e235c245dee5507b0e1b3f7196845d8d44a05076d667166a3df` |
| Wave 9 constitutional mutations | 12/12 killed; 0 invalid |
| Wave 9 bounded coverage ledger | 36/36 GREEN; 0 PARTIAL/orphan/evidence-free GREEN |
| Wave 9 release-conformance digest | `ded92c7e947ce2c3eeb82fb9b6fd36c3563e6b6fb71f5a3172450b48a8c98188` |
| Wave 9 coverage digest | `2f33d179b69238051ab2db1ba9a0662b52f6292450233bf2b18613ddf3ae6564` |
| Unit/integration discovery at pre-release head | 534 tests pass |
| Python matrix | 3.11 / 3.12 / 3.13 |

Pre-release implementation head `97ce80f13fd22e2347caf99e625865cfd2bb88f5` reproduced the complete historical + Wave-9 surface in CI run `33468034330`. Release closure additionally requires the exact `0.9.0a1` release head, pull-request synthetic merge and final `main` to reproduce the matrix.

## Wave-9 package map

| Module | Responsibility |
|---|---|
| `production_store` | storage capability profiles, authority epochs, durable exact-revision commit/CAS semantics |
| `destructive_compaction` | bounded prepare/shadow/switch/retire protocol and retention closure |
| `destructive_compaction_runtime` | kernel integration and restart-safe compaction state |
| `execution_contract` | adapter capability, cancellation, fencing, acknowledgement and compensation contracts |
| `execution_contract_runtime` | exact runtime binding of authorization to execution-contract semantics |
| `multiwriter` | writer identities, epoch leases and strong multi-writer coordination |
| `multiwriter_runtime` | kernel/storage authority-epoch binding and stale-authority rejection |
| `wave9_registry` | frozen DC/EX/MW + mutation + coverage invariant registry |
| `wave9_chaos` | deterministic production-fault schedules |
| `wave9_differential` | bounded live/restart/replay equivalence checks |
| `wave9_coverage` | final Wave-9 source/spec evidence audit |

Wave-8 falsification modules and all earlier kernel, proof, policy, schedulability, lineage, migration, replay and compaction modules remain mandatory regression surfaces.

## Research and engineering boundary

`GREEN` means tested correctness for the explicitly bounded reference-runtime contracts. It is not a formal proof of arbitrary production correctness and is not evidence of empirical superiority over other planning systems.

Wave 9 deliberately does **not** claim universal distributed consensus, arbitrary multi-host coordination, arbitrary database/storage-engine compaction or garbage collection, universal physical remote cancellation, or durability stronger than the storage/adapter capabilities actually declared and verified. The in-memory production-store implementation is a semantic reference, not itself a durable deployment backend.

Generalized open/opaque candidate-universe minimality, generalized constraint theories, arbitrary external historical schemas and benchmark superiority remain RESEARCH or BOUNDARY. No Wave-10+ surface is part of `0.9.0a1`.
