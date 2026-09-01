<div align="center">

# Nolane Plan

### Compile strategic futures. Carry proofs. Fail closed.

**A model-free, standard-library-first strategic future-space runtime for auditable AI-agent planning, replay, and execution authority.**

[English](README.md) · [Tiếng Việt](README-VN.md) · [简体中文](README-CN.md)

[![CI](https://github.com/Nolane-x/Nolane-Plan/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Nolane-x/Nolane-Plan/actions/workflows/ci.yml)
[![Release](https://img.shields.io/badge/release-v0.9.0a1-blue)](https://github.com/Nolane-x/Nolane-Plan/releases/tag/v0.9.0a1)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Dependencies](https://img.shields.io/badge/runtime%20dependencies-0-success)](pyproject.toml)
[![Model](https://img.shields.io/badge/model-free-runtime-purple)](#what-nolane-plan-is)

</div>

---

## Planning is not a checklist

Most agent planners produce a sequence, execute it, observe what happened, and replan. Nolane Plan starts from a different premise:

> **A serious plan is a bounded strategic future space with explicit state, evidence, uncertainty, authority, proof dependencies, contingencies, resource constraints, and replayable decisions.**

Instead of asking a model to remember all correctness-significant facts inside narration, Nolane Plan moves those facts into an executable runtime.

| Conventional agent planning | Nolane Plan |
|---|---|
| Plan → execute → replan | Compile and maintain a bounded future space |
| Model narration carries state | Canonical runtime state outranks narration |
| Hidden assumptions | Explicit evidence, uncertainty and blockers |
| One happy-path sequence | Sealed contingent policies and branch conditions |
| Retry after failure | Durable dispatch, reconciliation and compensation semantics |
| “Looks correct” | Deterministic conformance, mutation and coverage gates |
| Authority implied by control flow | Proof-carrying, lineage-bound execution authority |

## What Nolane Plan is

Nolane Plan is a **reference runtime for strategic planning correctness**. It is intentionally model-free: speculative/model workers can propose candidates, but correctness-significant state remains outside the model and is evaluated by the runtime.

The current architecture specification line is **v0.15**. The current implementation release is **`0.9.0a1`**, closing Wave 9: **Production Correctness / Distributed Authority**.

At a glance, the runtime provides:

- canonical state and principal-relative information;
- evidence, trust, uncertainty, blocker and proof dependency tracking;
- Decision Epochs and non-anticipative contingent policy selection;
- temporal, resource, schedulability and liveness checks;
- semantic lineage, replay, migration and bounded compaction;
- proof-carrying authorization and durable dispatch fencing;
- adapter-bound external execution, cancellation, reconciliation and compensation semantics;
- capability-qualified Authority Epochs for bounded strong multi-writer operation;
- deterministic conformance, chaos, differential, mutation and coverage gates.

## Core architecture

```text
                     speculative / model workers
                 ┌──────────┬──────────┬──────────┐
                 │          │          │          │
           principal A  principal B  verifier  ...
                 │          │          │
                 └──────────┴──────────┴──────────┘
                              │
                    ┌─────────▼─────────┐
                    │    PlanKernel     │
                    │ serialized truth │
                    └─────────┬─────────┘
                              │
      canonical state · evidence · trust · proof · policy
                              │
                principal-scoped Decision Epoch
                              │
              sealed contingent policy selection
                              │
        sufficiency · resources · deadlines · liveness
                              │
                 proof-carrying authorization
                              │
                    durable dispatch fence
                              │
                        external effect
                              │
          verify · reconcile · cancel · compensate
                              │
                       canonical commit
                              │
          journal · snapshot-v7 · fail-closed replay
                              │
             migration · lineage · safe compaction
                              │
            layered falsification and coverage
```

## `v0.9.0a1` — Production Correctness / Distributed Authority

Wave 9 does **not** add another planner. It hardens the already-established planning/proof/policy/replay stack across three bounded production surfaces.

| Surface | What the release closes |
|---|---|
| **Production store** | Storage capability profiles, exact-revision commit/CAS semantics and Authority Epochs |
| **Destructive compaction** | Prepare → shadow verification → durable switch → conservative retirement |
| **External execution** | Exact adapter capability/revision binding, dispatch, cancellation, reconciliation and compensation |
| **Multi-writer authority** | Strong multi-writer operation only where durable ACK + exact-revision CAS + fencing are actually available |
| **Restart / replay** | Correctness-significant Wave-9 sidecars survive supported restart and replay paths |
| **Falsification** | Deterministic chaos, differential equivalence, constitutional mutation and coverage evidence |

### Constitutional properties

The bounded runtime enforces, among others:

- **Canonical state outranks model narrative.**
- **A model cannot self-assert host/platform identity or execution authority.**
- Kernel-global visibility does not imply principal-available knowledge.
- Historical Decision Cuts do not acquire future information retroactively.
- Proof authority binds captured dependencies, freshness and support/blocker semantics.
- Hard vetoes cannot be scored back into eligibility.
- Non-anticipative policy cannot branch on information unavailable to the acting principal.
- Joint resource feasibility is not inferred from per-job feasibility.
- Semantic-regime or exact-lineage drift invalidates stale authority before dispatch.
- Migration mappings cannot mint or resurrect authorization.
- Unknown correctness-significant replay events fail closed.
- Representation-only compaction cannot erase protected lineage or strengthen authority.
- Cancellation after durable dispatch cannot be reported as clean cancellation without reconciliation evidence.
- Ambiguous relocation remains ambiguous; opaque/global theories remain `UNKNOWN` rather than optimistically composable.

## Quick start

```bash
git clone https://github.com/Nolane-x/Nolane-Plan.git
cd Nolane-Plan
python -m pip install -e .
python -m nolane_plan demo --root .demo-plan
```

Run the full unit/integration suite:

```bash
python -m unittest discover -s tests -v
```

Run the current Wave-9 evidence gates:

```bash
python -m nolane_plan.wave9_chaos
python -m nolane_plan.wave9_differential
python scripts/wave9_mutation_gate.py
python -m nolane_plan.wave9_coverage
```

Resume a saved runtime:

```python
from nolane_plan import PlanKernel

kernel = PlanKernel.open(".demo-plan")
```

`PlanKernel.open()` is a correctness operation, not a permissive loader: unsupported or correctness-significant unknown state fails closed.

## Frozen release evidence

The `0.9.0a1` runtime release commit is:

```text
d11abb4468c701622d0e78722f1a0e54c94aa920
```

That exact runtime release line was closed through release-head CI, pull-request synthetic-merge CI, and a fresh final-`main` CI matrix on Python **3.11 / 3.12 / 3.13** before later presentation-only documentation changes.

| Gate | Frozen result |
|---|---:|
| Unit/integration discovery at pre-release implementation head | 534 tests pass |
| Principal-scope projection oracle | v0.14 `108` collisions → v0.15 `0` |
| Wave 2 adversarial conformance | 10/10 |
| Wave 3 adversarial / mutations | 12/12 + 4/4 |
| Wave 4 adversarial / mutations | 14/14 + 7/7 |
| Wave 5 adversarial / mutations | 29/29 + 13/13 |
| Wave 6 adversarial / mutations | 43/43 + 12/12 |
| Wave 7 adversarial / mutations | 32/32 + 12/12 |
| Wave 8 unified conformance / mutations / coverage | GREEN + 12/12 killed, 0 invalid + GREEN |
| Wave 9 registry | 56 invariants |
| Wave 9 deterministic production-fault schedules | 12/12 |
| Wave 9 differential equivalence | 4/4 |
| Wave 9 constitutional mutations | 12/12 killed; 0 invalid |
| Wave 9 bounded coverage ledger | 36/36 GREEN; 0 PARTIAL/orphan/evidence-free GREEN |
| Python matrix | 3.11 / 3.12 / 3.13 |

<details>
<summary><strong>Frozen Wave-9 digests</strong></summary>

```text
Registry
15e4876c1fabe75bbfe78c5f3a921299315863277bc791ac5324bf6115204ea8

Chaos
acd59b52184cea99cd5101fde9cb83c74f947b207af813c6ac81388eaf60e01a

Differential
14ab39e4b32a5e235c245dee5507b0e1b3f7196845d8d44a05076d667166a3df

Release conformance
ded92c7e947ce2c3eeb82fb9b6fd36c3563e6b6fb71f5a3172450b48a8c98188

Coverage
2f33d179b69238051ab2db1ba9a0662b52f6292450233bf2b18613ddf3ae6564
```

</details>

## Package map

| Module | Responsibility |
|---|---|
| `PlanKernel` / core runtime | canonical correctness writer and runtime coordination |
| `production_store` | storage capability profiles, Authority Epochs, exact-revision durable commit/CAS semantics |
| `destructive_compaction` | bounded prepare/shadow/switch/retire protocol and retention closure |
| `destructive_compaction_runtime` | kernel integration and restart-safe compaction state |
| `execution_contract` | adapter capability, cancellation, fencing, acknowledgement and compensation contracts |
| `execution_contract_runtime` | exact authorization-to-adapter contract binding |
| `multiwriter` | writer identities, epoch leases and strong multi-writer coordination |
| `multiwriter_runtime` | storage/kernel authority binding and stale-authority rejection |
| `wave9_registry` | frozen Wave-9 invariant registry |
| `wave9_chaos` | deterministic production-fault schedules |
| `wave9_differential` | bounded live/restart/replay equivalence checks |
| `wave9_coverage` | final source/spec evidence audit |

Earlier proof, policy, schedulability, liveness, lineage, migration, replay, compaction and Wave-8 falsification modules remain mandatory regression surfaces.

## What Nolane Plan deliberately does **not** claim

`GREEN` means tested correctness for the exact bounded contracts represented by the repository. It does **not** mean universal formal correctness or empirical superiority over every planner.

`0.9.0a1` does not claim:

- universal distributed consensus;
- arbitrary multi-host crash safety;
- arbitrary database/storage-engine garbage-collection or compaction safety;
- universal physical remote cancellation;
- durability stronger than the declared storage/adapter capabilities;
- generalized open-world candidate-universe minimality;
- generalized arbitrary constraint-theory completeness;
- benchmark superiority over other planning systems;
- any Wave-10+ capability.

The in-memory production store is a **semantic reference backend**, not itself a claim of production durable storage.

## Documentation

- [`CONFORMANCE.md`](CONFORMANCE.md) — executable correctness/evidence surface.
- [`SECURITY.md`](SECURITY.md) — security and trust boundaries.
- [`CHANGELOG.md`](CHANGELOG.md) — release history.
- [`docs/superpowers/specs/`](docs/superpowers/specs/) — checked-in architecture/design specifications.
- [`docs/superpowers/plans/`](docs/superpowers/plans/) — implementation plans and closure contracts.
- [`docs/releases/v0.9.0a1.md`](docs/releases/v0.9.0a1.md) — release notes for the current runtime line.

## Languages

- **English:** [`README.md`](README.md)
- **Tiếng Việt:** [`README-VN.md`](README-VN.md)
- **简体中文:** [`README-CN.md`](README-CN.md)

## License

Nolane Plan is released under the [MIT License](LICENSE).

---

<div align="center">

**Nolane Plan** — strategic futures should be executable, inspectable, replayable, and falsifiable.

</div>
