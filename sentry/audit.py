from dataclasses import dataclass, field


@dataclass
class AuditEntry:
    action: str
    status: str  # "executed" | "refused" | "waited"
    reason: str


@dataclass
class AuditLog:
    entries: list = field(default_factory=list)

    def record(self, entry: AuditEntry) -> None:
        self.entries.append(entry)

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
        return len(self.entries)

    def render(self) -> str:
        lines = [
            f"[{entry.status.upper():8}] {entry.action} - {entry.reason}"
            for entry in self.entries
        ]
        return "\n".join(lines)
