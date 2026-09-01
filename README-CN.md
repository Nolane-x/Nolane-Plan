<div align="center">

# Nolane Plan

### 编译战略未来空间。携带证明。默认失败关闭。

**一个不依赖模型、优先使用 Python 标准库的战略未来空间运行时，用于可审计的 AI Agent 规划、重放与执行权限控制。**

[English](README.md) · [Tiếng Việt](README-VN.md) · [简体中文](README-CN.md)

[![CI](https://github.com/Nolane-x/Nolane-Plan/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Nolane-x/Nolane-Plan/actions/workflows/ci.yml)
[![Release](https://img.shields.io/badge/release-v0.9.0a1-blue)](https://github.com/Nolane-x/Nolane-Plan/releases/tag/v0.9.0a1)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Dependencies](https://img.shields.io/badge/runtime%20dependencies-0-success)](pyproject.toml)
[![Model](https://img.shields.io/badge/model-free-runtime-purple)](#什么是-nolane-plan)

</div>

---

## 规划不应只是一个清单

大多数 Agent Planner 会生成步骤序列、执行、观察结果，然后重新规划。Nolane Plan 从一个不同的前提出发：

> **真正严肃的计划，应当是一个有界的战略未来空间，其中状态、证据、不确定性、权限、证明依赖、条件分支与资源约束都被显式表示。**

Nolane Plan 不要求模型在自然语言叙述中“记住”所有影响正确性的事实，而是把这些事实放进可执行、可重放、可审计的运行时状态中。

| 常规 Agent Planning | Nolane Plan |
|---|---|
| Plan → execute → replan | 编译并维护有界未来空间 |
| 模型叙述承载状态 | Canonical runtime state 高于模型叙述 |
| 隐含假设 | 显式 evidence、uncertainty 与 blocker |
| 单一 happy path | Sealed contingent policy 与 branch condition |
| 失败后重试 | Durable dispatch、reconciliation 与 compensation |
| “看起来正确” | 确定性的 conformance、mutation 与 coverage gate |
| 权限隐藏在控制流中 | Proof-carrying、lineage-bound execution authority |

## 什么是 Nolane Plan

Nolane Plan 是一个面向**战略规划正确性**的 reference runtime。它刻意保持 model-free：模型或 speculative worker 可以提出 candidate，但所有对正确性有意义的状态都由运行时掌控，而不是由模型自行声明。

当前架构规格线为 **v0.15**。当前实现 release 为 **`0.9.0a1`**，对应已经关闭的 Wave 9：**Production Correctness / Distributed Authority**。

当前运行时提供：

- canonical state 与 principal-relative information；
- evidence、trust、uncertainty、blocker 与 proof dependency；
- Decision Epoch 与 non-anticipative contingent policy selection；
- temporal、resource、schedulability 与 liveness 检查；
- semantic lineage、replay、migration 与 bounded compaction；
- proof-carrying authorization 与 durable dispatch fencing；
- 与 adapter capability/revision 精确绑定的 external execution、cancellation、reconciliation 与 compensation；
- 基于 capability 的 Authority Epoch 与 bounded strong multi-writer；
- 确定性的 conformance、chaos、differential、mutation 与 coverage gate。

## 核心架构

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

Wave 9 **并没有增加第二套 Planner**。它是在已有 planning/proof/policy/replay 栈之上，对三个明确有界的 production surface 进行强化。

| Surface | 本次 release 关闭的能力 |
|---|---|
| **Production store** | Storage capability profile、exact-revision commit/CAS 与 Authority Epoch |
| **Destructive compaction** | Prepare → shadow verification → durable switch → conservative retirement |
| **External execution** | 精确 adapter capability/revision 绑定、dispatch、cancellation、reconciliation 与 compensation |
| **Multi-writer authority** | 只有后端真实具备 durable ACK + exact-revision CAS + fencing 时才允许 strong multi-writer |
| **Restart / replay** | Wave-9 correctness-significant sidecar 在支持的 restart/replay 路径上得到保留 |
| **Falsification** | Deterministic chaos、differential equivalence、constitutional mutation 与 coverage evidence |

### 关键“宪法级”性质

这个有界运行时会强制执行以下性质，其中包括：

- **Canonical state 高于 model narrative。**
- **模型不能自行声明 host/platform identity 或 execution authority。**
- Kernel-global visibility 不代表某个 principal 实际拥有该信息。
- Historical Decision Cut 不会追溯性地看到未来 artifact。
- Proof authority 绑定已捕获的 dependency、freshness、support 与 blocker semantics。
- Hard veto 不能通过打分重新变为 eligible。
- Non-anticipative policy 不能基于当前 principal 尚不可获得的信息分支。
- Joint resource feasibility 不能只从单个 job 的可行性推断。
- Semantic-regime 或 exact-lineage drift 会在 dispatch 前使 stale authority 失效。
- Migration mapping 不能凭空创建或复活 authorization。
- 未知但影响 correctness 的 replay event 必须 fail closed。
- Representation-only compaction 不能删除 protected lineage 或增强 authority。
- Durable dispatch 之后的 cancellation，在缺少 reconciliation evidence 时不能被报告为 clean cancellation。
- 仍然存在歧义的 relocation 必须保持歧义；opaque/global theory 应保持 `UNKNOWN`，而不是被乐观地组合。

## 快速开始

```bash
git clone https://github.com/Nolane-x/Nolane-Plan.git
cd Nolane-Plan
python -m pip install -e .
python -m nolane_plan demo --root .demo-plan
```

运行完整 unit/integration suite：

```bash
python -m unittest discover -s tests -v
```

运行当前 Wave 9 evidence gates：

```bash
python -m nolane_plan.wave9_chaos
python -m nolane_plan.wave9_differential
python scripts/wave9_mutation_gate.py
python -m nolane_plan.wave9_coverage
```

重新打开已保存的 runtime：

```python
from nolane_plan import PlanKernel

kernel = PlanKernel.open(".demo-plan")
```

`PlanKernel.open()` 是 correctness operation，而不是宽松 loader。对于不受支持或无法识别但会影响正确性的状态，系统会 fail closed。

## 冻结的 release evidence

`0.9.0a1` 的 runtime release commit：

```text
d11abb4468c701622d0e78722f1a0e54c94aa920
```

这个完全相同的 runtime release line 在后续仅文档展示层变更之前，已经通过 release-head CI、pull-request synthetic-merge CI，以及 Python **3.11 / 3.12 / 3.13** 的 fresh final-`main` CI matrix 完成关闭。

| Gate | 冻结结果 |
|---|---:|
| Pre-release implementation head 的 unit/integration discovery | 534 tests pass |
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
<summary><strong>冻结的 Wave-9 digests</strong></summary>

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

| Module | 职责 |
|---|---|
| `PlanKernel` / core runtime | canonical correctness writer 与 runtime coordination |
| `production_store` | storage capability、Authority Epoch、exact-revision durable commit/CAS |
| `destructive_compaction` | bounded prepare/shadow/switch/retire 与 retention closure |
| `destructive_compaction_runtime` | kernel integration 与 restart-safe compaction state |
| `execution_contract` | adapter capability、cancellation、fencing、acknowledgement 与 compensation |
| `execution_contract_runtime` | 将 authorization 精确绑定到 adapter contract |
| `multiwriter` | writer identity、epoch lease 与 strong multi-writer coordination |
| `multiwriter_runtime` | storage/kernel authority binding 与 stale-authority rejection |
| `wave9_registry` | 冻结的 Wave-9 invariant registry |
| `wave9_chaos` | deterministic production-fault schedules |
| `wave9_differential` | bounded live/restart/replay equivalence |
| `wave9_coverage` | Wave 9 最终 source/spec evidence audit |

更早的 proof、policy、schedulability、liveness、lineage、migration、replay、compaction 与 Wave-8 falsification module 仍然是强制 regression surface。

## Nolane Plan 明确**不**声称什么

`GREEN` 只表示 repository 中明确有界 contract 的 tested correctness。它**不**代表任意场景下的全局形式化正确性，也不代表实证上优于所有 planner。

`0.9.0a1` 不声称：

- universal distributed consensus；
- arbitrary multi-host crash safety；
- 任意 database/storage-engine 的 garbage collection 或 compaction safety；
- universal physical remote cancellation；
- 超过 storage/adapter 明确声明 capability 的 durability；
- generalized open-world candidate-universe minimality；
- 任意 constraint theory 的 generalized completeness；
- 对其他 planning system 的 benchmark superiority；
- 任何 Wave-10+ capability。

In-memory production store 只是一个 **semantic reference backend**，并不等价于 production durable storage。

## 文档

- [`CONFORMANCE.md`](CONFORMANCE.md) — 可执行的 correctness/evidence surface。
- [`SECURITY.md`](SECURITY.md) — security 与 trust boundary。
- [`CHANGELOG.md`](CHANGELOG.md) — release 历史。
- [`docs/superpowers/specs/`](docs/superpowers/specs/) — 已提交的 architecture/design spec。
- [`docs/superpowers/plans/`](docs/superpowers/plans/) — implementation plan 与 closure contract。
- [`docs/releases/v0.9.0a1.md`](docs/releases/v0.9.0a1.md) — 当前 runtime line 的 release notes。

## 语言

- **English:** [`README.md`](README.md)
- **Tiếng Việt:** [`README-VN.md`](README-VN.md)
- **简体中文:** [`README-CN.md`](README-CN.md)

## License

Nolane Plan 使用 [MIT License](LICENSE) 发布。

---

<div align="center">

**Nolane Plan** — 战略未来应当可执行、可检查、可重放、可证伪。

</div>
