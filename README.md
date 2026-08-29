# Nolane Plan

**Strategic Future-Space Runtime for AI Agents — v0.15 reference implementation line**

Nolane Plan is not a longer task list and not a generate-plan/execute/replan wrapper. It treats planning as compilation of a bounded strategic future space: future families, decision-relevant strategic states, obligations, uncertainty, residual/unknown worlds, evidence dependencies, convergence, temporal reaction constraints and principal-scoped execution authority.

This repository contains a **model-free, standard-library-first reference runtime** derived from the Nolane Plan v0.15 architecture specification. It is designed to make semantic mistakes executable and testable rather than leaving them as conventions for an implementation to guess.

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
               principal-bound authorization
                          |
                    dispatch fence
                          |
                    external adapter
                          |
                postcondition verification
                          |
                   canonical commit
```

### Constitutional properties implemented

- canonical reality/state outranks model narrative;
- mission versions invalidate stale completion/decision artifacts;
- `NULL_WORLD` is always representable;
- principal identity is distinct from role/model/process/session/grant;
- kernel-global knowledge is not automatically principal-available knowledge;
- Decision Capsules are recipient- and information-scope-bound;
- hydration cannot escalate a principal's information scope;
- ActionAuthorization binds the exact acting principal;
- dispatch rechecks the presented principal and grant freshness;
- authority-sensitive receipts preserve executing-principal attribution;
- Strategic Obligations remain condition-centric across worker loss/replacement;
- evidence independence is lineage-based, not message/agent count;
- hard-veto actions are not rescued by scalar score optimization;
- unknown/model-class anomalies quarantine consequential actions;
- branch pruning keeps dormant/resurrection semantics and refuses unique hedges;
- universal/absence claims require complete, current query snapshots;
- derived proof artifacts stale when declared dependency generations change;
- action transport success is not canonical commit without postcondition verification;
- correctness mutations are hash-journaled under one serialized writer.

## Quick start

```bash
python -m nolane_plan conformance
python -m nolane_plan demo --root .demo-plan
python -m unittest discover -s tests -v
```

The conformance command reproduces the v0.15 principal-scope bounded oracle:

```text
principals                           4
information decisions             128
authorization decisions            16
v0.14 information collisions       96
v0.14 authorization collisions     12
v0.14 total collisions             108
v0.15 challenger collisions         0
```

## Package map

| Module | Responsibility |
|---|---|
| `kernel` | serialized correctness writer and end-to-end lifecycle |
| `mission` | versioned mission contract |
| `principals` | access/delivery partitions and principal-bound decision epochs |
| `evidence` | polarity, provenance lineage, freshness-sensitive support |
| `future` / `compiler` | future families, NULL_WORLD, strategic lattice, convergence |
| `obligations` | condition-centric strategic obligations |
| `capsule` | bounded recipient-scoped decision projections |
| `actions` | grants, authorization, dispatch eligibility and receipts |
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
| `conformance` | bounded v0.15 falsification/oracle suite |

## Research status

This repository is a **reference implementation**, not a claim that Nolane Plan is empirically superior to existing planners, POMDP systems, HTN planners, MCTS systems, or production agent frameworks. Bounded conformance tests are strong evidence against specific semantic shortcuts; they are not a global proof of correctness.

The next valid semantic revision should be driven by executable counterexample, differential implementation mismatch, adapter experiment, replay/migration conflict, or bounded/formal trace—not by adding prose because more features are imaginable.
