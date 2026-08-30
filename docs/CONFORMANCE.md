# v0.15 Conformance Surface

Nolane Plan uses bounded deterministic falsification suites. These gates defend specific semantic contracts; they are not a proof of distributed safety, global correctness or empirical planning superiority.

## Principal-scope oracle

The original principal-scope oracle constructs four principals and two classes of bounded experiments.

For information decisions it evaluates 32 scenarios × 4 principals = 128 decisions. Sixteen scenarios are principal-sensitive. Under a v0.14-style projection that omits principal identity, every sensitive scenario collapses four decision contexts into one projection, yielding `C(4,2)=6` incompatible pairs per scenario: `16 × 6 = 96` collisions. Under the v0.15 projection, principal scope is part of the projection and collisions fall to zero.

For authorization it evaluates 4 intended principals × 4 presented principals = 16 decisions. A v0.14 bearer-style projection collapses the presenter; each intended authorization has one legal presenter and three illegal presenters, producing 3 incompatible pairs × 4 cases = 12 collisions. Acting/presented principal binding removes them.

Total bounded distinction: `96 + 12 = 108` v0.14 collision pairs → `0` under the v0.15 challenger.

Run:

```bash
python -m nolane_plan conformance
```

## Wave-specific adversarial gates

The release matrix additionally runs deterministic wave-specific suites:

```bash
python -m nolane_plan.wave2_conformance   # 10/10 runtime-closure cases
python -m nolane_plan.wave3_conformance   # 12/12 external-trust cases
python -m nolane_plan.wave4_conformance   # 14/14 proof-dependency/support cases
python -m nolane_plan.wave5_conformance   # 29/29 executable-policy cases
```

Wave 5 covers principal-relative non-anticipativity, policy coherence, hard-veto selection, selection freshness/supersession, recursive recall, outcome totality, policy-edge stitching, bounded N-way proof-context composition, reaction controllability, structure-aware preparedness, information-capability preservation, continuation horizons, exact-scope executability and monotonic PlanSeal invalidation.

## Constitutional mutation gates

The mutation scripts deliberately remove or weaken constitutional checks and require the focused tests to kill every mutant:

```bash
python scripts/wave3_mutation_gate.py   # 4/4
python scripts/wave4_mutation_gate.py   # 7/7
python scripts/wave5_mutation_gate.py   # 13/13
```

The Wave-5 mutation gate targets non-anticipativity bypass, hard-veto bypass, selection freshness bypass, recursive-recall shortcut, missing-successor laundering, global-composition UNSAT bypass, worst-case reaction bypass, information-capability-loss bypass, continuation-horizon bypass, kernel executability/selection bypasses, policy internal-digest bypass and seal revival.

## Release matrix

For `0.5.0a1`, GitHub Actions runs the same correctness surface on Python 3.11, 3.12 and 3.13:

1. install editable package;
2. 248 unit/integration tests;
3. compile all `src` modules;
4. principal-scope `108 -> 0` oracle;
5. Wave 2–5 adversarial conformance;
6. Wave 3–5 constitutional mutation gates;
7. end-to-end demo.

A GREEN wave therefore means the bounded repository gates found no surviving counterexample in that implemented scope. It does not upgrade unimplemented Wave-6 schedulability/handoff semantics, full replay/migration exhaustion, distributed correctness or empirical superiority into proved properties.
