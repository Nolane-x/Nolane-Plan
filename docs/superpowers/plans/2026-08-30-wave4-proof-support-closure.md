# Wave 4 — Proof Dependency & Support Closure Implementation Plan

## Task 1 — Proof input envelope and capture assurance

**RED:** add `tests/test_wave4_proof_inputs.py` covering enforced-envelope completeness, trusted dynamic capture binding, self-report rejection for strong reuse, hidden-read rejection, opaque/unsupported capture ceilings, and canonical digest stability.

**GREEN:** implement `src/nolane_plan/proof_inputs.py`.

## Task 2 — Query-domain negative dependencies

**RED:** add `tests/test_wave4_query_domain.py` covering zero-result non-proof, current complete snapshot, membership generation drift, predicate/schema/visibility drift, existing-member predicate mutation sensitivity, and opaque/incomplete domains.

**GREEN:** implement `src/nolane_plan/query_domain.py` and compatibility bridge from existing `query.py`.

## Task 3 — Proof dependency manifest and freshness vector

**RED:** add `tests/test_wave4_dependency_manifest.py` covering exact revision drift, domain generation drift, query-domain drift, trust/profile dependencies, capture gaps, weak capture assurance, and conservative over-approximation.

**GREEN:** implement `src/nolane_plan/proof_dependencies.py` without deleting the older lightweight `DependencyManifest` API.

## Task 4 — Bounded alternative-support algebra

**RED:** add `tests/test_wave4_support.py` covering OR alternatives, conjunctive clause retraction, empty-support vacuity, context mismatch, circular grounding, duplicate common roots, support/invalidation duality, and historical immutable assessments.

**GREEN:** implement `src/nolane_plan/support.py`.

## Task 5 — Semantic closure barrier

**RED:** add `tests/test_wave4_semantic_barrier.py` proving source revision and affected freshness generations advance atomically, stale proof authority fails immediately, unknown impact needs conservative fallback, and cached validity cannot override a mismatch.

**GREEN:** implement `src/nolane_plan/semantic_barrier.py`.

## Task 6 — Kernel proof-authority integration

**RED:** add `tests/test_wave4_kernel_proof_authority.py` covering strong proof registration, unsupported proof rejection, blocker rejection, source-mutation staleness before authorization, query-domain invalidation, and weak/self-reported capture rejection.

**GREEN:** add a narrow `proof_runtime.py` extension installed on the existing `PlanKernel`; do not create another correctness writer.

## Task 7 — Durable proof lineage and derived-state reconstruction

**RED:** add `tests/test_wave4_replay.py` covering snapshot/reopen of proof envelopes/manifests/support lineage and a post-snapshot source mutation that must not resurrect stale authority.

**GREEN:** add a Wave-4 recovery extension layered after trust recovery. Persist canonical proof lineage; recompute/recheck derived support/freshness before authority.

## Task 8 — Adversarial conformance and mutations

Add deterministic Wave-4 conformance focused on hidden reads, negative dependencies, support retraction, semantic closure ordering, and crash/replay. Add deliberate mutations for at least: self-report elevation, membership-generation omission, empty-support vacuity, blocker/support conflation, freshness bypass, and mutation-without-generation-bump.

## Task 9 — Release gate

- full unit suite
- compileall
- v0.14→v0.15 principal oracle
- Wave 2 conformance
- Wave 3 conformance + mutations
- Wave 4 conformance + mutations
- demo
- Python 3.11/3.12/3.13
- update `SPEC-COVERAGE.md` only for proven surfaces
- bump `0.4.0a1`
- merge only from fresh green exact head
- rerun exact merge commit on `main`
