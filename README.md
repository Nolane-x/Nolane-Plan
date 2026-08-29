# Nolane Plan

**Strategic Future-Space Runtime for AI Agents — v0.15 reference implementation line**

Nolane Plan is not a longer task list and not a generate-plan/execute/replan wrapper. It treats planning as compilation of a bounded strategic future space: future families, decision-relevant strategic states, obligations, uncertainty, residual/unknown worlds, evidence dependencies, convergence, temporal reaction constraints and principal-scoped execution authority.

This repository contains a **model-free, standard-library-first reference runtime** derived from the Nolane Plan v0.15 architecture specification. It is designed to make semantic mistakes executable and testable rather than leaving them as conventions for an implementation to guess.

## Runtime line

`0.2.0a1` is the Wave 2 runtime-closure line. It keeps one serialized correctness writer while making causal cuts, proof freshness, adapter assurance, ambiguous side-effect reconciliation and verified crash resume part of the executable authority path.

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
        +-----------------+------------------+
        |                 |                  |
 canonical state   strategic future     evidence/freshness
        |                 |                  |
        +--------- Decision Capsules --------+
                          |
                    Decision Cut
                          |
               principal-bound authorization
                          |
              adapter capability binding
                          |
             durable dispatch transaction
                          |
                    external effect
                          |
           verify / reconcile ambiguous outcome
                          |
                   canonical commit
```

### Constitutional properties implemented

- canonical reality/state outranks model narrative;
- mission versions invalidate stale completion/decision artifacts;
- `NULL_WORLD` is always representable;
- principal identity is distinct from role/model/process/session/grant;
- kernel-global knowledge is not automatically principal-available knowledge;
- Decision Capsules are recipient-, information-scope- and Decision-Cut-bound;
- hydration cannot escalate a principal's information scope;
- proof artifacts stale immediately when bound freshness generations change;
- an artifact committed after a historical Decision Cut is not visible retroactively;
- ActionAuthorization binds the exact acting principal and may bind an exact adapter revision;
- executor-sensitive consequential actions require adapter principal attestation and a dispatch fence;
- dispatch is durably recorded before the external adapter is invoked;
- ambiguous external outcomes move to `RECONCILIATION_REQUIRED`;
- non-idempotent ambiguous actions cannot blind-retry before trusted reconciliation;
- transport success alone is never canonical commit without postcondition verification;
- universal/absence claims require complete, current query snapshots;
- preparedness and reaction-window constraints can block consequential authorization;
- strategic relocation preserves ambiguity; `UNLOCATED` enters model-class uncertainty;
- completion is a cut/freshness-bound proof artifact rather than a timeless boolean;
- snapshot restore verifies digest, hash-chain and journal-prefix binding;
- unknown post-snapshot mutation semantics fail closed during replay;
- correctness mutations remain under one serialized writer.

## Quick start

```bash
python -m nolane_plan conformance
python -m nolane_plan.wave2_conformance
python -m nolane_plan demo --root .demo-plan
python -m unittest discover -s tests -v
```

Resume a previously saved runtime:

```python
from nolane_plan import PlanKernel

kernel = PlanKernel.open(".demo-plan")
```

`PlanKernel.open()` is a correctness operation, not a permissive loader. The snapshot must verify, its stored journal head must identify a real prefix of the current journal, and every post-snapshot event must have a known replay reducer.

The original principal-scope conformance command reproduces:

```text
principals                           4
information decisions             128
authorization decisions            16
v0.14 information collisions       96
v0.14 authorization collisions     12
v0.14 total collisions             108
v0.15 challenger collisions         0
```

Wave 2 adds a separate deterministic 10-case adversarial suite covering causal-cut leakage, authority-time freshness, adapter assurance, non-idempotent reconciliation, universal-query completeness, reaction schedulability, resource conflict, unknown-world relocation, completion-proof freshness and snapshot/journal-prefix binding.

## Package map

| Module | Responsibility |
|---|---|
| `kernel` | serialized correctness writer and end-to-end lifecycle |
| `decision_cut` | prefix-closed causal authority views |
| `artifacts` | authority-time proof/artifact freshness and cut visibility |
| `execution` | adapter capability profiles and durable action transactions |
| `resume` | snapshot schema v2, verified restore and fail-closed suffix replay |
| `mission` | versioned mission contract |
| `principals` | access/delivery partitions and principal-bound decision epochs |
| `evidence` | polarity, provenance lineage, freshness-sensitive support |
| `future` / `compiler` | future families, NULL_WORLD, strategic lattice, convergence |
| `obligations` | condition-centric strategic obligations |
| `capsule` | bounded recipient-scoped decision projections |
| `actions` | grants, principal/cut/adapter-bound authorization and receipts |
| `action_lifecycle` | strict proposal→verification→commit transaction state machine |
| `temporal` | reaction and handoff liveness contracts |
| `recovery` | model-class uncertainty quarantine |
| `freshness` / `dependency` | dependency generation binding and artifact invalidation |
| `query` | universal/absence enumeration completeness receipts |
| `pruning` | safe dormancy and revalidation-based resurrection |
| `preparedness` | horizon/irreversibility-sensitive preparedness floors |
| `policy` | principal-relative non-anticipativity checking |
| `resources` | shared/exclusive commitment conflict checking |
| `relocation` | LOCATED/AMBIGUOUS/UNLOCATED strategic relocation |
| `budget` | mandatory-first bounded planning work allocation |
| `verification` | success/obligation/anti-goal completion proof surface |
| `persistence` | hash-chained journal and verified snapshots |
| `conformance` | bounded v0.15 principal-scope falsification/oracle suite |
| `wave2_conformance` | deterministic runtime-closure adversarial suite |

## Research status

This repository is a **reference implementation**, not a claim that Nolane Plan is empirically superior to existing planners, POMDP systems, HTN planners, MCTS systems, or production agent frameworks. Bounded conformance tests are strong evidence against specific semantic shortcuts; they are not a global proof of correctness.

The next valid semantic revision should be driven by executable counterexample, differential implementation mismatch, adapter experiment, replay/migration conflict, or bounded/formal trace—not by adding prose because more features are imaginable.
