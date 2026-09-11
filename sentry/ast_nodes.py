from dataclasses import dataclass, field


@dataclass
class FieldAccess:
    base: str
    field: str


@dataclass
class ActionCall:
    name: str
    args: list = field(default_factory=list)
