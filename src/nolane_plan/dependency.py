from __future__ import annotations

from dataclasses import dataclass

from .freshness import DependencyStamp, FreshnessDomainLedger


@dataclass(frozen=True, slots=True)
class DependencyManifest:
    stamp: DependencyStamp
    assurance: str

    @classmethod
    def capture(cls, ledger: FreshnessDomainLedger, domains: tuple[str, ...], assurance: str) -> "DependencyManifest":
        return cls(DependencyStamp.capture(ledger, domains), assurance)

    def current(self, ledger: FreshnessDomainLedger) -> bool:
        return self.stamp.current(ledger)


@dataclass(frozen=True, slots=True)
class DerivedArtifact:
    id: str
    dependency_manifest: DependencyManifest

    def current(self, ledger: FreshnessDomainLedger) -> bool:
        return self.dependency_manifest.current(ledger)
