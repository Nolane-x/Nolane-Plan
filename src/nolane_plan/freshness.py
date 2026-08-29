from __future__ import annotations

from dataclasses import dataclass


class FreshnessDomainLedger:
    def __init__(self) -> None:
        self.generations: dict[str, int] = {}

    def ensure(self, domain: str) -> int:
        return self.generations.setdefault(domain, 1)

    def bump(self, domain: str) -> int:
        self.generations[domain] = self.generations.get(domain, 1) + 1
        return self.generations[domain]

    def generation(self, domain: str) -> int:
        return self.generations.get(domain, 1)


@dataclass(frozen=True, slots=True)
class DependencyStamp:
    generations: tuple[tuple[str, int], ...]

    @classmethod
    def capture(cls, ledger: FreshnessDomainLedger, domains: tuple[str, ...]) -> "DependencyStamp":
        return cls(tuple(sorted((d, ledger.generation(d)) for d in domains)))

    def current(self, ledger: FreshnessDomainLedger) -> bool:
        return all(ledger.generation(domain) == generation for domain, generation in self.generations)
