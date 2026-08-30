# Nolane Plan

**Strategic Future-Space Runtime for AI Agents — v0.15 reference implementation line**

Nolane Plan is not a longer task list and not a generate-plan/execute/replan wrapper. It treats planning as compilation of a bounded strategic future space: future families, decision-relevant strategic states, obligations, uncertainty, residual/unknown worlds, evidence dependencies, contingent policies, temporal reaction constraints and principal-scoped execution authority.

This repository contains a **model-free, standard-library-first reference runtime** derived from the Nolane Plan v0.15 architecture specification. Its purpose is to make semantic shortcuts executable, falsifiable and replayable rather than leaving them as conventions for an implementation to guess.

## Runtime line

`0.5.0a1` is the Wave-5 executable-policy-closure line. It preserves one serialized correctness writer while adding principal-information-feasible contingent policy, frozen advisory selection, decision sufficiency, PlanSeal, recall/totality/stitch certificates, bounded reaction/readiness semantics, exact-scope executability and snapshot-v5 replay to the authority path.

Wave 5 does **not** claim joint control-plane schedulability, repeated handoff liveness, activation-time edge stability, distributed correctness writers, formal global correctness or empirical superiority. Those remain outside this release's bounded claim surface.

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

### Constitutional properties implemented

- canonical reality/state outranks model narrative;
- mission versions invalidate stale completion and decision artifacts;
- `NULL_WORLD` remains representable;
- principal identity is distinct from role/model/process/session/grant;
- runtime-global knowledge is not automatically principal-available knowledge;
- Decision Capsules are recipient-, information-scope- and Decision-Cut-bound;
- hydration cannot escalate a principal's information scope;
- proof artifacts stale when bound semantic/query/freshness dependencies change;
- historical Decision Cuts do not see future artifacts retroactively;
- strong identity is host/platform-bound rather than model-narrated;
- inter-principal knowledge requires recipient/time-grounded observation evidence;
- dispatch and strong reconciliation bind exact principal, transaction and adapter evidence;
- policy splits must respect principal-relative information equivalence before grounded reveal;
- `SelectionRecord` is advisory only; hard vetoes cannot be resurrected by score;
- PlanSeal cannot self-promote assurance, hide unaccepted debt or revive after monotonic invalidation;
- recursive recall compares downstream decision signatures rather than only the current action;
- supported outcomes require exact valid successor/reconciliation/residual handling; generic catch-alls are not totality proofs;
- parent→child policy edges require explicit stitch/refinement compatibility;
- IA1 possible timing is not treated as IA2 bounded reaction guarantee;
- information-destroying actions are blocked unless a robust information-independent continuation is explicit;
- deferred/unknown continuation does not silently extend the certified executable horizon;
- `EXEC_BOUNDED` requires a current exact-scope closure rather than score/confidence promotion;
- sealed-policy authorization still delegates through existing proof and identity authority binders;
- dispatch is durably recorded before an external adapter is invoked;
- non-idempotent ambiguous effects cannot blind-retry before evidence-bound reconciliation;
- snapshot restore verifies outer and policy-internal digests, hash-chain/prefix binding and supported suffix reducers;
- stale selection/seal/executability state does not resurrect on replay;
- correctness-significant mutations remain under one serialized writer.

## Quick start

```bash
python -m pip install -e .
python -m nolane_plan conformance
python -m nolane_plan.wave2_conformance
python -m nolane_plan.wave3_conformance
python -m nolane_plan.wave4_conformance
python -m nolane_plan.wave5_conformance
python scripts/wave3_mutation_gate.py
python scripts/wave4_mutation_gate.py
python scripts/wave5_mutation_gate.py
python -m unittest discover -s tests -v
python -m nolane_plan demo --root .demo-plan
```

Resume a previously saved runtime:

```python
from nolane_plan import PlanKernel

kernel = PlanKernel.open(".demo-plan")
```

`PlanKernel.open()` is a correctness operation, not a permissive loader. The snapshot must verify, its stored journal head must identify a real prefix of the current journal, policy/proof/trust internal digests must reconstruct canonically, and every correctness-significant post-snapshot event must have a known replay reducer for the implemented surface.

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

Additional deterministic bounded gates currently include:

- Wave 2 runtime-closure adversarial suite: 10 cases;
- Wave 3 external-trust adversarial suite: 12 cases, plus 4 constitutional mutations;
- Wave 4 proof-dependency/support adversarial suite: 14 cases, plus 7 constitutional mutations;
- Wave 5 executable-policy adversarial suite: 29 cases, plus 13 constitutional mutations.

The `0.5.0a1` release head is gated on Python 3.11, 3.12 and 3.13 by 248 unit/integration tests, compile, the original principal oracle, all Wave 2–5 adversarial suites, Wave 3–5 mutation gates and the end-to-end demo.

## Package map

| Module | Responsibility |
|---|---|
| `kernel` | serialized correctness writer and end-to-end lifecycle |
| `decision_cut` | prefix-closed causal authority views |
| `artifacts` | authority-time proof/artifact freshness and cut visibility |
| `trust_runtime` / `trust_recovery` | host-grounded identity, communication, dispatch/reconciliation evidence and replay |
| `proof_runtime` / `proof_recovery` | proof dependency/support authority integration and replay |
| `policy_information` | principal-scoped partitions, epochs, reveals, frontiers and non-anticipativity |
| `policy_ir` | contingent policy nodes and policy-level coherence |
| `selection` | frozen selection transactions and advisory freshness-bound records |
| `seals` / `seal_lifecycle` | sufficiency, proof-context composition, PlanSeal and monotonic invalidation |
| `policy_certificates` | recursive recall, totality and policy-edge stitch certificates |
| `policy_readiness` | reaction envelopes, preparedness, information capability and continuation |
| `policy_executability` | exact-scope `EXEC_*` closure assessment |
| `policy_runtime` / `policy_recovery` | sealed-policy authority integration and snapshot-v5 replay |
| `execution` | adapter capability profiles and durable action transactions |
| `resume` | lower-layer verified restore and fail-closed suffix replay |
| `mission` | versioned mission contract |
| `principals` | base access/delivery partitions |
| `evidence` | polarity, provenance lineage and freshness-sensitive support |
| `future` / `compiler` | future families, `NULL_WORLD`, strategic lattice and convergence |
| `obligations` | condition-centric strategic obligations |
| `capsule` | bounded recipient-scoped decision projections |
| `actions` | grants, principal/cut/adapter-bound authorization and receipts |
| `action_lifecycle` | proposal→verification→commit transaction semantics |
| `temporal` | base reaction and handoff contracts |
| `recovery` | model-class uncertainty quarantine |
| `freshness` / `dependency` | dependency generation binding and invalidation |
| `query` | universal/absence enumeration completeness |
| `pruning` | dormancy and revalidation-based resurrection |
| `preparedness` | base horizon/irreversibility preparedness floors |
| `resources` | shared/exclusive commitment conflict checking |
| `relocation` | LOCATED/AMBIGUOUS/UNLOCATED strategic relocation |
| `budget` | mandatory-first bounded planning work allocation |
| `verification` | success/obligation/anti-goal completion proof surface |
| `persistence` | hash-chained journal and verified snapshots |
| `conformance` | bounded v0.15 principal-scope falsification/oracle suite |
| `wave2_conformance` … `wave5_conformance` | wave-specific adversarial falsification suites |

## Research status

This repository is a **reference implementation**, not a claim that Nolane Plan is empirically superior to existing planners, POMDP systems, HTN planners, MCTS systems or production agent frameworks. Bounded conformance and mutation tests are evidence against specific semantic shortcuts; they are not a global formal proof.

The next closure wave is Wave 6: joint schedulability/liveness and future-temporal-resource integration. New semantics should continue to be driven by executable counterexamples, differential mismatch, replay/migration conflict, adapter experiments or bounded/formal traces rather than by prose expansion alone.
