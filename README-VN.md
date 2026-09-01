<div align="center">

# Nolane Plan

### Biên dịch không gian tương lai chiến lược. Mang theo bằng chứng. Fail closed.

**Một strategic future-space runtime không phụ thuộc model, ưu tiên Python standard library, dành cho lập kế hoạch AI agent có thể kiểm toán, replay và kiểm soát quyền thực thi.**

[English](README.md) · [Tiếng Việt](README-VN.md) · [简体中文](README-CN.md)

[![CI](https://github.com/Nolane-x/Nolane-Plan/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Nolane-x/Nolane-Plan/actions/workflows/ci.yml)
[![Release](https://img.shields.io/badge/release-v0.9.0a1-blue)](https://github.com/Nolane-x/Nolane-Plan/releases/tag/v0.9.0a1)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Dependencies](https://img.shields.io/badge/runtime%20dependencies-0-success)](pyproject.toml)
[![Model](https://img.shields.io/badge/model-free-runtime-purple)](#nolane-plan-là-gì)

</div>

---

## Lập kế hoạch không chỉ là một checklist

Phần lớn planner cho agent tạo ra một chuỗi bước, thực thi, quan sát kết quả rồi replan. Nolane Plan bắt đầu từ một giả định khác:

> **Một kế hoạch nghiêm túc là một không gian tương lai chiến lược có giới hạn, trong đó trạng thái, bằng chứng, bất định, authority, proof dependency, contingency và ràng buộc tài nguyên đều phải được biểu diễn rõ ràng.**

Thay vì bắt model phải “nhớ” toàn bộ các sự thật ảnh hưởng đến correctness trong phần narration, Nolane Plan đưa chúng ra ngoài model và biến chúng thành trạng thái runtime có thể thực thi, replay và kiểm toán.

| Agent planning thông thường | Nolane Plan |
|---|---|
| Plan → execute → replan | Biên dịch và duy trì bounded future space |
| Model narration mang trạng thái | Canonical runtime state quan trọng hơn narration |
| Giả định ẩn | Evidence, uncertainty và blocker tường minh |
| Một happy path | Sealed contingent policy và branch condition |
| Thất bại rồi retry | Durable dispatch, reconciliation và compensation |
| “Có vẻ đúng” | Conformance, mutation và coverage gate xác định |
| Authority ngầm trong control flow | Proof-carrying, lineage-bound execution authority |

## Nolane Plan là gì

Nolane Plan là một **reference runtime cho correctness của strategic planning**. Runtime cố ý không phụ thuộc model: model/speculative workers có thể đề xuất candidate, nhưng trạng thái có ý nghĩa đối với correctness không được giao cho model tự quyết định.

Dòng đặc tả kiến trúc hiện tại là **v0.15**. Release implementation hiện tại là **`0.9.0a1`**, đóng Wave 9: **Production Correctness / Distributed Authority**.

Runtime hiện cung cấp:

- canonical state và thông tin theo từng principal;
- evidence, trust, uncertainty, blocker và proof dependency;
- Decision Epoch và non-anticipative contingent policy selection;
- kiểm tra temporal, resource, schedulability và liveness;
- semantic lineage, replay, migration và bounded compaction;
- proof-carrying authorization và durable dispatch fencing;
- external execution gắn chặt adapter capability/revision, cancellation, reconciliation và compensation;
- Authority Epoch có điều kiện capability cho bounded strong multi-writer;
- conformance, chaos, differential, mutation và coverage gate xác định.

## Kiến trúc lõi

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

Wave 9 **không tạo thêm một planner mới**. Nó harden stack planning/proof/policy/replay hiện có trên ba bề mặt production được giới hạn rõ ràng.

| Bề mặt | Release đóng được gì |
|---|---|
| **Production store** | Storage capability profile, exact-revision commit/CAS và Authority Epoch |
| **Destructive compaction** | Prepare → shadow verification → durable switch → conservative retirement |
| **External execution** | Binding chính xác adapter capability/revision, dispatch, cancellation, reconciliation và compensation |
| **Multi-writer authority** | Strong multi-writer chỉ khi backend thật sự có durable ACK + exact-revision CAS + fencing |
| **Restart / replay** | Correctness-significant sidecar của Wave 9 sống qua supported restart/replay |
| **Falsification** | Deterministic chaos, differential equivalence, constitutional mutation và coverage evidence |

### Các thuộc tính “hiến pháp” quan trọng

Runtime bounded này cưỡng chế, trong số nhiều điều khác:

- **Canonical state luôn đứng trên model narrative.**
- **Model không thể tự khai báo host/platform identity hoặc execution authority.**
- Kernel-global visibility không đồng nghĩa principal có quyền biết thông tin đó.
- Historical Decision Cut không được nhìn thấy artifact tương lai một cách hồi tố.
- Proof authority gắn với dependency đã capture, freshness, support và blocker semantics.
- Hard veto không thể bị score để quay trở lại trạng thái eligible.
- Non-anticipative policy không được branch trên thông tin mà principal chưa có.
- Joint resource feasibility không được suy ra chỉ từ từng job riêng lẻ.
- Semantic-regime hoặc exact-lineage drift làm stale authority mất hiệu lực trước dispatch.
- Migration mapping không thể tự tạo hoặc hồi sinh authorization.
- Replay event không biết nhưng ảnh hưởng correctness phải fail closed.
- Representation-only compaction không được xóa protected lineage hoặc tăng authority.
- Cancellation sau durable dispatch không thể bị báo thành clean cancellation nếu thiếu reconciliation evidence.
- Relocation còn mơ hồ phải tiếp tục là mơ hồ; opaque/global theory vẫn là `UNKNOWN` thay vì được suy diễn lạc quan.

## Bắt đầu nhanh

```bash
git clone https://github.com/Nolane-x/Nolane-Plan.git
cd Nolane-Plan
python -m pip install -e .
python -m nolane_plan demo --root .demo-plan
```

Chạy toàn bộ unit/integration suite:

```bash
python -m unittest discover -s tests -v
```

Chạy các gate Wave 9 hiện tại:

```bash
python -m nolane_plan.wave9_chaos
python -m nolane_plan.wave9_differential
python scripts/wave9_mutation_gate.py
python -m nolane_plan.wave9_coverage
```

Mở lại runtime đã lưu:

```python
from nolane_plan import PlanKernel

kernel = PlanKernel.open(".demo-plan")
```

`PlanKernel.open()` là một correctness operation, không phải permissive loader. Trạng thái không được hỗ trợ hoặc correctness-significant nhưng không nhận diện được sẽ fail closed.

## Bằng chứng release đã đóng băng

Runtime release commit của `0.9.0a1` là:

```text
d11abb4468c701622d0e78722f1a0e54c94aa920
```

Exact runtime release line này đã được đóng qua release-head CI, pull-request synthetic-merge CI và fresh final-`main` CI trên Python **3.11 / 3.12 / 3.13** trước các thay đổi presentation-only về sau.

| Gate | Kết quả đóng băng |
|---|---:|
| Unit/integration discovery ở pre-release implementation head | 534 tests pass |
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
<summary><strong>Wave-9 digests đã đóng băng</strong></summary>

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

| Module | Trách nhiệm |
|---|---|
| `PlanKernel` / core runtime | canonical correctness writer và runtime coordination |
| `production_store` | storage capability, Authority Epoch, exact-revision durable commit/CAS |
| `destructive_compaction` | bounded prepare/shadow/switch/retire và retention closure |
| `destructive_compaction_runtime` | tích hợp kernel và compaction state restart-safe |
| `execution_contract` | adapter capability, cancellation, fencing, acknowledgement và compensation |
| `execution_contract_runtime` | bind authorization chính xác vào adapter contract |
| `multiwriter` | writer identity, epoch lease và strong multi-writer coordination |
| `multiwriter_runtime` | storage/kernel authority binding và stale-authority rejection |
| `wave9_registry` | registry invariant Wave 9 đóng băng |
| `wave9_chaos` | deterministic production-fault schedules |
| `wave9_differential` | bounded live/restart/replay equivalence |
| `wave9_coverage` | source/spec evidence audit cuối Wave 9 |

Các module proof, policy, schedulability, liveness, lineage, migration, replay, compaction và Wave-8 falsification trước đó vẫn là regression surface bắt buộc.

## Nolane Plan cố ý **không** tuyên bố điều gì

`GREEN` chỉ có nghĩa là correctness đã được kiểm thử cho đúng các bounded contract mà repository biểu diễn. Nó **không** có nghĩa là formal proof toàn cục hoặc tốt hơn mọi planner khác trên thực nghiệm.

`0.9.0a1` không tuyên bố:

- universal distributed consensus;
- arbitrary multi-host crash safety;
- an toàn garbage collection/compaction cho mọi database/storage engine;
- universal physical remote cancellation;
- durability mạnh hơn capability mà storage/adapter thật sự khai báo;
- generalized open-world candidate-universe minimality;
- completeness cho mọi loại arbitrary constraint theory;
- benchmark superiority so với planner khác;
- bất kỳ capability Wave 10+ nào.

In-memory production store chỉ là **semantic reference backend**, không phải bằng chứng cho production durable storage thực tế.

## Tài liệu

- [`CONFORMANCE.md`](CONFORMANCE.md) — bề mặt correctness/evidence thực thi được.
- [`SECURITY.md`](SECURITY.md) — security và trust boundary.
- [`CHANGELOG.md`](CHANGELOG.md) — lịch sử release.
- [`docs/superpowers/specs/`](docs/superpowers/specs/) — architecture/design spec đã check in.
- [`docs/superpowers/plans/`](docs/superpowers/plans/) — implementation plan và closure contract.
- [`docs/releases/v0.9.0a1.md`](docs/releases/v0.9.0a1.md) — release notes của runtime hiện tại.

## Ngôn ngữ

- **English:** [`README.md`](README.md)
- **Tiếng Việt:** [`README-VN.md`](README-VN.md)
- **简体中文:** [`README-CN.md`](README-CN.md)

## Giấy phép

Nolane Plan được phát hành theo [MIT License](LICENSE).

---

<div align="center">

**Nolane Plan** — strategic future nên có thể thực thi, kiểm tra, replay và falsify.

</div>
