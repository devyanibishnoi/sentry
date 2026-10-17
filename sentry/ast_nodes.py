from dataclasses import dataclass, field
from typing import Optional, Union


@dataclass
class FieldAccess:
    root: str
    path: list = field(default_factory=list)
    line: int = field(default=0, compare=False)
    column: int = field(default=0, compare=False)


@dataclass
class Literal:
    value: object  # str, int, or float


Expression = Union[FieldAccess, Literal]


@dataclass
class Comparison:
    left: Expression
    operator: str
    right: Expression
    line: int = field(default=0, compare=False)
    column: int = field(default=0, compare=False)


@dataclass
class ApprovalRequired:
    pass


Gate = Union[Comparison, ApprovalRequired]


@dataclass
class ActionCall:
    name: str
    args: list = field(default_factory=list)
    gate: Optional[Gate] = None
    line: int = field(default=0, compare=False)
    column: int = field(default=0, compare=False)


@dataclass
class Duration:
    amount: int
    unit: str  # "s", "m", or "h"


@dataclass
class WaitStmt:
    duration: Duration
    line: int = field(default=0, compare=False)
    column: int = field(default=0, compare=False)


@dataclass
class IfElse:
    condition: Comparison
    then_body: list
    else_body: Optional[list] = None
    line: int = field(default=0, compare=False)
    column: int = field(default=0, compare=False)


Statement = Union[ActionCall, IfElse, WaitStmt]


@dataclass
class OnBlock:
    name: str
    body: list = field(default_factory=list)


@dataclass
class Program:
    on_blocks: list = field(default_factory=list)
