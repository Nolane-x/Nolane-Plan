# v0.15 Conformance Surface

The deterministic principal-scope oracle constructs four principals and two classes of bounded experiments.

For information decisions it evaluates 32 scenarios × 4 principals = 128 decisions. Sixteen scenarios are principal-sensitive. Under a v0.14-style projection that omits principal identity, every sensitive scenario collapses four decision contexts into one projection, yielding `C(4,2)=6` incompatible pairs per scenario: `16 × 6 = 96` collisions. Under the v0.15 projection, principal scope is part of the projection and collisions fall to zero.

For authorization it evaluates 4 intended principals × 4 presented principals = 16 decisions. A v0.14 bearer-style projection collapses the presenter; each intended authorization has one legal presenter and three illegal presenters, producing 3 incompatible pairs × 4 cases = 12 collisions. Acting/presented principal binding removes them.

Total bounded distinction: `96 + 12 = 108` v0.14 collision pairs → `0` under the v0.15 challenger.

Run:

```bash
python -m nolane_plan conformance
```

The oracle is a falsification aid, not proof of distributed multi-agent safety or empirical planning superiority.
