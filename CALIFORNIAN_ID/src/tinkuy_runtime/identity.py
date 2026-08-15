"""Implementation identity — proof of which code actually ran.

Every binding result carries one of these. It is not decoration: the whole
question this pass answers is "did a native organ execute, or did something
reconstruct its output?", and the only durable answer is the file, the hash and
the qualified name of the callable that produced the value.
"""
from __future__ import annotations

import hashlib
import inspect
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ImplementationIdentity:
    """Which callable, in which file, at which content hash."""
    organ: str
    qualname: str
    module: str
    source_path: str
    source_sha256: str
    lineno: int
    #: MODEL_FREE — no model was involved in producing the value.
    #: MODEL_BACKED — a model boundary was crossed inside the implementation.
    execution_kind: str = "MODEL_FREE"

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def identify(organ: str, fn: Callable[..., Any],
             execution_kind: str = "MODEL_FREE") -> ImplementationIdentity:
    """Describe the callable we are about to delegate to.

    Resolved from the live object, not from a string: a renamed or moved
    implementation changes the identity instead of silently keeping a stale
    label.
    """
    module = inspect.getmodule(fn)
    try:
        source_file = Path(inspect.getsourcefile(fn) or "")
    except TypeError:
        source_file = Path("")
    try:
        lineno = inspect.getsourcelines(fn)[1]
    except (OSError, TypeError):
        lineno = 0
    try:
        rel = str(source_file.resolve().relative_to(REPO_ROOT))
    except (ValueError, OSError):
        rel = str(source_file)
    return ImplementationIdentity(
        organ=organ,
        qualname=getattr(fn, "__qualname__", repr(fn)),
        module=getattr(module, "__name__", "?"),
        source_path=rel.replace("\\", "/"),
        source_sha256=_sha256_file(source_file),
        lineno=lineno,
        execution_kind=execution_kind,
    )


@dataclass
class BindingResult:
    """What a native binding returns: the value, or an explicit absence.

    There is deliberately no third state. A binding that cannot reach its organ
    returns ``available=False`` with a reason; it never returns a substitute,
    and callers cannot mistake one for the other because ``value`` is None.
    """
    organ: str
    call: str
    available: bool
    value: Any = None
    reason: str = ""
    identity: ImplementationIdentity | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_public(self) -> dict[str, Any]:
        return {
            "organ": self.organ,
            "call": self.call,
            "available": self.available,
            "reason": self.reason,
            "identity": self.identity.to_public() if self.identity else None,
            "provenance": self.provenance,
            "value": self.value,
        }

    def unwrap(self) -> Any:
        if not self.available:
            raise NativeOrganUnavailable(f"{self.call}: {self.reason}")
        return self.value


class NativeOrganUnavailable(RuntimeError):
    """Raised when a caller demands a value the organ could not produce."""
