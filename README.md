# Nolane Plan

**Strategic Future-Space Runtime for AI Agents — v0.15 reference implementation line**

Nolane Plan treats planning as compilation of a bounded strategic future space rather than a longer checklist or a plan→execute→replan wrapper. The runtime keeps canonical state, future families, obligations, uncertainty, principal-relative information, proof dependencies, contingent policy, temporal/resource constraints, semantic lineage and execution authority outside model narration and makes correctness-significant shortcuts executable, replayable and auditable.

This repository is a **model-free, standard-library-first reference runtime** derived from the Nolane Plan v0.15 architecture specification.

## Runtime line

`0.7.0a1` is the Wave-7 durable-lineage, semantic-migration, replay and reversible-compaction closure line.

It preserves one serialized correctness writer and extends the Wave-6 authority path with:

- a common immutable `CanonicalLineageRevision` sidecar for declared strategic runtime families, with stable logical identity, exact revision identity, parent/provenance/debt lineage and deterministic semantic digests;
- explicit immutable schema, world-model, environment, canonicalization and semantic-profile regime revisions;
- exact DecisionEpoch and authorization lineage closure across mission/canonical/action, proof, policy, schedulability and semantic-regime dependencies;
- a frozen replay registry covering every correctness-significant `_record(...)` event emitted by the bounded runtime, with fail-closed unknown events and deterministic base-event reconstruction;
- snapshot schema v7 carrying lineage, regimes, migration, compaction, replay-registry and exact authority-lineage state, plus conservative deterministic v6 import;
- typed semantic migrations using exactly six dispositions, explicit identity/debt handling, authority invalidation/recheck and verified bridges for ambiguous external actions;
- representation-only reversible compaction with read-only archive/reconstruction semantics that preserve active authority, dormant/resurrection, proof/evidence/debt and unique-fallback lineage;
- exact 32-case Wave-7 adversarial conformance and a 12-mutant constitutional gate.

Wave 7 deliberately does **not** claim every historical schema-pair migration, arbitrary destructive production-storage compaction, distributed correctness writers, property/metamorphic/chaos/differential exhaustion, production hardening, formal global correctness or empirical superiority.

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
             exact immutable authority lineage
                               |
               principal/adapter dispatch fence
                               |
                         external effect
                               |
              verify / reconcile ambiguous outcome
                               |
                        canonical commit
                               |
             journal + snapshot-v7 + replay registry
                               |
      semantic migration / reversible lineage compaction
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
- blocking invalidity cannot be replaced by absence of a blocker or positive support alone;
- contingent policy splits obey principal-relative non-anticipativity;
- `SelectionRecord` is advisory; hard vetoes cannot be resurrected by score;
- PlanSeal assurance cannot self-promote and invalidated seals cannot revive;
- recursive recall compares downstream decision signatures;
- totality remains distinct from open-world model adequacy;
- local reaction feasibility does not imply joint policy schedulability;
- deadline-critical planning capacity is protected from speculative work;
- repeated `SAFE_HANDOFF` cannot indefinitely rename, defer or self-extend required continuation work;
- activation-time generation, permission, reservation, writer and open-side-effect state is refreshed before child entry;
- fallback count does not create robustness when routes share a declared common-mode dependency;
- dormant protected branches cannot resurrect without current revalidation of bound semantic dimensions;
- logical identity never substitutes for exact authority-bearing revision identity;
- semantic-regime drift blocks stale authorization before dispatch;
- migration mapping alone never revives invalidated authority;
- ambiguous external actions cannot be reinterpreted across schema migration without a verified bridge;
- replay uses serialized journal sequence rather than wall time and unknown correctness-significant events fail closed;
- compaction cannot erase protected lineage or strengthen authority, and reconstruction must reproduce the certified semantic root;
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
python -m nolane_plan.wave7_conformance
python scripts/wave7_mutation_gate.py
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
| Wave 6 adversarial / mutations | 43/43 + 12/12 |
| Wave 7 adversarial / mutations | 32/32 + 12/12 |
| Unit/integration suite | 408/408 |
| Python release matrix | 3.11 / 3.12 / 3.13 |

The Wave-7 release gate also requires source compilation, the original `108 -> 0` oracle, all Wave 2–7 gates and the end-to-end demo on each matrix entry. See `CONFORMANCE.md` for the exact claim boundary.

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
| `handoff_liveness` / `handoff_stability` | bounded handoff progress and activation-time freshness |
| `policy_coverage` / `option_independence` | model adequacy and common-mode-aware robustness |
| `future_resurrection` | revisioned dormancy/resurrection revalidation |
| `schedulability_runtime` / `schedulability_recovery` | Wave-6 authority prerequisites and persistence |
| `lineage` / `lineage_runtime` | immutable strategic lineage and explicit semantic regimes |
| `migration` / `migration_runtime` | typed six-disposition semantic migration and authority recheck |
| `replay_registry` / `lineage_recovery` / `lineage_snapshot` | frozen correctness-event replay and snapshot-v7 closure |
| `compaction` / `compaction_runtime` | reversible representation-only lineage compaction and reconstruction |
| `authority_lineage_runtime` / `authority_lineage_patch` | exact DecisionEpoch/authorization lineage closure and dispatch currentness |
| `execution` | adapter capability profiles and durable action transactions |
| `future` / `compiler` | future families, `NULL_WORLD`, strategic lattice and bounded compilation |
| `obligations` | condition-centric strategic obligations |
| `budget` / `resources` | protected planning capacity and shared commitments |
| `persistence` / `resume` | journal/snapshot integrity and lower-layer replay |
| `conformance`, `wave2_conformance` … `wave7_conformance` | bounded executable falsification suites |

## Research and engineering boundary

This repository is a reference implementation, not evidence that Nolane Plan is empirically superior to existing planners, POMDP systems, HTN planners, MCTS systems or production agent frameworks. Passing bounded conformance and mutation gates means specific encoded shortcuts were rejected at the tested scope; it is not a global formal proof.

Wave 8 is the next normative engineering tranche: property/metamorphic/chaos/differential exhaustion, broader constitutional mutants, bounded reference worlds/benchmarks and final source-spec coverage reconciliation. Empirical superiority remains a measurement question, not a correctness claim.
