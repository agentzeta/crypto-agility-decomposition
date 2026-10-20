"""Diagnostic bookkeeping for a fixed legacy-object migration population.

This module verifies input consistency and computes a counting identity. It
does not discover objects, verify migration evidence, authorize updates, or
prove closure. Capability labels apply throughout the declared scenario window.
Success fractions may be observations or assumptions; label them accordingly.

Fractions are exact rational values. A float is interpreted using its shortest
decimal string, not its underlying binary expansion. Already-rounded inputs
cannot be repaired. Reported fractions and amounts are JSON-safe ratio strings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from fractions import Fraction
from math import isfinite
from typing import Any, Dict, Optional, Tuple, Union

__version__ = "0.3.0"
Number = Union[int, float, Fraction]


def _number(name: str, value: Number) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise ValueError(f"{name} must be an int, float or Fraction, excluding bool")
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{name} must be finite")
        return Fraction(str(value))
    return Fraction(value)


def _fraction(name: str, value: Number) -> Fraction:
    result = _number(name, value)
    if not 0 <= result <= 1:
        raise ValueError(f"{name} must be in [0, 1]")
    return result


class MechanismSupport(str, Enum):
    NONE = "NONE"
    PROPOSED = "PROPOSED"
    IMPLEMENTED = "IMPLEMENTED"
    ACTIVATED = "ACTIVATED"
    OPERATIONAL = "OPERATIONAL"

    @property
    def usable(self) -> bool:
        """Activated is a declared scenario capability, not a coverage proof."""
        return self in (self.ACTIVATED, self.OPERATIONAL)


class ObjectContinuity(str, Enum):
    """Identity of the primary object, not downstream compatibility."""
    RECREATED = "RECREATED"
    PRESERVED = "PRESERVED"


class TransitionAuthority(str, Enum):
    """Available paths throughout the scenario window.

    INDEPENDENT_PATH may coexist with incumbent action. Availability is not
    successful execution. NOBODY means neither kind of path is available.
    """
    NOBODY = "NOBODY"
    INCUMBENT_ONLY = "INCUMBENT_ONLY"
    INDEPENDENT_PATH = "INDEPENDENT_PATH"

    @property
    def can_act_without_incumbent(self) -> bool:
        return self is self.INDEPENDENT_PATH


class Outcome(str, Enum):
    TRANSITIONED = "TRANSITIONED"
    DISABLED = "DISABLED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class Assessment:
    """Assessment of a fixed population and disjoint successful-transition sets.

    r counts incumbent successes first; q counts independent successes only
    among the remainder, even when both paths could serve the same object.
    All fractions use the same weights. Disabled means continuity has not
    been restored and is therefore part of the NOT-SUCCESSFULLY-TRANSITIONED
    residual. Its optional fraction is over the whole assessed weight.

    population_known is a record count. Non-object weighting additionally
    requires weight_known and weight_unit. Coverage is record coverage, not
    value/path coverage or evidence of reachability/completeness.
    """
    system: str
    scope: str
    weighting: str = "objects"
    evaluated_at: str = ""
    mechanism: MechanismSupport = MechanismSupport.NONE
    continuity: ObjectContinuity = ObjectContinuity.RECREATED
    authority: TransitionAuthority = TransitionAuthority.INCUMBENT_ONLY
    population_known: int = 0
    population_believed_total: Optional[int] = None
    r_incumbent: Number = 0
    q_independent: Number = 0
    disabled_fraction: Optional[Number] = None
    weight_known: Optional[Number] = None
    weight_unit: str = ""
    note: str = ""
    assumptions: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name in ("system", "scope"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be nonempty text")
        for name in ("evaluated_at", "note", "weight_unit"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"{name} must be text")
        if self.evaluated_at:
            try:
                parsed = date.fromisoformat(self.evaluated_at)
            except ValueError as exc:
                raise ValueError("evaluated_at must be YYYY-MM-DD or empty") from exc
            if parsed.isoformat() != self.evaluated_at:
                raise ValueError("evaluated_at must be YYYY-MM-DD or empty")
        for name, cls in (("mechanism", MechanismSupport),
                          ("continuity", ObjectContinuity),
                          ("authority", TransitionAuthority)):
            if not isinstance(getattr(self, name), cls):
                raise ValueError(f"{name} must be a {cls.__name__} member")
        for name in ("population_known", "population_believed_total"):
            value = getattr(self, name)
            if name == "population_believed_total" and value is None:
                continue
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if (self.population_believed_total is not None and
                self.population_believed_total < self.population_known):
            raise ValueError("believed total cannot be smaller than known population")
        if self.weighting not in ("objects", "value", "authority_paths"):
            raise ValueError("weighting must be objects, value or authority_paths")
        if not isinstance(self.assumptions, (tuple, list)) or any(
                not isinstance(x, str) or not x.strip() for x in self.assumptions):
            raise ValueError("assumptions must be a sequence of nonempty strings")
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        r = _fraction("r_incumbent", self.r_incumbent)
        q = _fraction("q_independent", self.q_independent)
        object.__setattr__(self, "r_incumbent", r)
        object.__setattr__(self, "q_independent", q)
        if self.population_known == 0 and (r or q):
            raise ValueError("empty population requires r=q=0")
        if not self.mechanism.usable and (r or q):
            raise ValueError("successes require a usable mechanism in this scenario")
        if self.authority is TransitionAuthority.NOBODY and (r or q):
            raise ValueError("NOBODY cannot report successful transitions")
        if q and not self.authority.can_act_without_incumbent:
            raise ValueError("q>0 requires INDEPENDENT_PATH")
        if r == 1 and q:
            raise ValueError("use q=0 when r=1: the remainder is empty")
        if self.weighting == "objects":
            if self.weight_known is not None or self.weight_unit:
                raise ValueError("object weighting uses population_known and implicit object units")
        else:
            if self.weight_known is None or not self.weight_unit.strip():
                raise ValueError("non-object weighting requires weight_known and weight_unit")
            weight = _number("weight_known", self.weight_known)
            if weight < 0 or (self.population_known > 0 and weight == 0):
                raise ValueError("nonempty assessed population needs positive total weight")
            if self.population_known == 0 and weight:
                raise ValueError("empty population must have zero weight")
            object.__setattr__(self, "weight_known", weight)
        if self.disabled_fraction is not None:
            disabled = _fraction("disabled_fraction", self.disabled_fraction)
            if disabled > (1 - r) * (1 - q) or (not self.population_known and disabled):
                raise ValueError("disabled fraction cannot exceed the not-transitioned residual")
            object.__setattr__(self, "disabled_fraction", disabled)

    def residual_fraction(self) -> Optional[Fraction]:
        """Fraction NOT successfully transitioned, including disabled objects.

        No rounding and no capability override of reported successes. None
        denotes an empty denominator, not a zero-percent failure finding.
        """
        if not self.population_known:
            return None
        return (1 - self.r_incumbent) * (1 - self.q_independent)

    def residual_amount(self) -> Fraction:
        """Unrounded residual in declared units; may be an assumed equivalent."""
        residual = self.residual_fraction()
        if residual is None:
            return Fraction(0)
        weight = self.population_known if self.weighting == "objects" else self.weight_known
        return weight * residual

    def residual_count(self) -> int:
        """Integral object-equivalent count only; never round or infer from value.

        An integer computed from assumed inputs is still not an observed count.
        Use residual_amount() for fractional equivalents or weighted amounts.
        """
        if self.weighting != "objects":
            raise ValueError("weighted residuals cannot be converted to object counts")
        amount = self.residual_amount()
        if amount.denominator != 1:
            raise ValueError("fractional object equivalents are not an integral count")
        return amount.numerator

    def coverage(self) -> Dict[str, Any]:
        total = self.population_believed_total
        fraction = Fraction(self.population_known, total) if total else None
        return {"known_records": self.population_known, "believed_total_records": total,
                "record_coverage_fraction": None if fraction is None else str(fraction),
                "statement": "Record coverage only, relative to a declared believed total; "
                             "not a reachability, weight-coverage or completeness proof. "
                             "Results hold within the assessed population only."}

    def dependent_breakage(self) -> Dict[str, Any]:
        return {"object_continuity": self.continuity.value,
                "primary_identity_preserved": self.continuity is ObjectContinuity.PRESERVED,
                "breaks_external_references": None,
                "creates_other_objects": None,
                "statement": "Primary identity alone does not determine downstream "
                             "compatibility, proof updates, session behavior or other objects. "
                             "Assess those dependencies separately."}

    def outcome_fractions(self) -> Dict[str, Optional[Fraction]]:
        residual = self.residual_fraction()
        if residual is None:
            return {o.value: None for o in Outcome}
        disabled = self.disabled_fraction
        if residual == 0:
            disabled = Fraction(0)
        return {Outcome.TRANSITIONED.value: 1 - residual,
                Outcome.DISABLED.value: disabled,
                Outcome.UNRESOLVED.value: None if disabled is None else residual - disabled}

    def report(self) -> Dict[str, Any]:
        residual = self.residual_fraction()
        amount = self.residual_amount()
        count = (amount.numerator if self.weighting == "objects" and amount.denominator == 1
                 else None)
        return {"system": self.system, "scope": self.scope,
                "weighting": self.weighting, "evaluated_at": self.evaluated_at,
                "A_M_mechanism": self.mechanism.value,
                "A_R_continuity": self.continuity.value,
                "A_C_coverage": self.coverage(), "A_T_authority": self.authority.value,
                "r_incumbent": str(self.r_incumbent), "q_independent": str(self.q_independent),
                "not_transitioned_fraction": None if residual is None else str(residual),
                "residual_amount": str(amount),
                "amount_unit": "objects" if self.weighting == "objects" else self.weight_unit,
                "integral_object_equivalents": count,
                "outcome_fractions": {k: None if v is None else str(v)
                                      for k, v in self.outcome_fractions().items()},
                "dependent_breakage": self.dependent_breakage(),
                "assumptions": list(self.assumptions), "note": self.note,
                "interpretation": "Computed from declared inputs; not verified outcomes. "
                                  "Ratio strings are exact for those inputs. A_C only "
                                  "reports declared record coverage."}


def authority_effect(r: Number = 0.8) -> Dict[str, Any]:
    """Availability contrast with both achieved-success fractions held fixed."""
    rows = []
    for authority in (TransitionAuthority.INCUMBENT_ONLY, TransitionAuthority.INDEPENDENT_PATH):
        a = Assessment(system=authority.value, scope="synthetic fixed-input comparison",
                       mechanism=MechanismSupport.ACTIVATED, authority=authority,
                       continuity=ObjectContinuity.PRESERVED, population_known=1000,
                       r_incumbent=r, q_independent=0)
        rows.append({"authority": authority.value, "r": a.r_incumbent, "q": a.q_independent,
                     "residual_fraction": a.residual_fraction()})
    return {"varied": "authority availability", "held_constant": "mechanism, continuity, N, r, q=0",
            "rows": rows, "statement": "An available independent path with no achieved "
                    "independent successes does not reduce the residual. NOBODY is excluded "
                    "because positive r would contradict that configuration."}


def independent_success_effect(r: Number = 0.8) -> Dict[str, Any]:
    """Vary assumed q while keeping authority availability and r fixed."""
    r = _fraction("r", r)
    if r == 1:
        raise ValueError("q comparison needs a nonempty remainder")
    rows = []
    for q in (0, Fraction(1, 2), 1):
        a = Assessment(system="synthetic independent path", scope="assumed success sensitivity",
                       mechanism=MechanismSupport.ACTIVATED,
                       authority=TransitionAuthority.INDEPENDENT_PATH,
                       continuity=ObjectContinuity.PRESERVED, population_known=1000,
                       r_incumbent=r, q_independent=q,
                       assumptions=("q is an assumed successful share of the remainder, "
                                    "not inferred from path availability",))
        rows.append({"authority": a.authority.value, "r": a.r_incumbent,
                     "q": a.q_independent, "residual_fraction": a.residual_fraction(),
                     "assumptions": list(a.assumptions)})
    return {"varied": "assumed q", "held_constant": "mechanism, continuity, authority, N, r",
            "rows": rows, "statement": "Arithmetic sensitivity, not an empirical causal experiment."}


def continuity_effect(r: Number = 0.8) -> Dict[str, Any]:
    rows = []
    for continuity in ObjectContinuity:
        a = Assessment(system=continuity.value, scope="synthetic fixed-input comparison",
                       mechanism=MechanismSupport.ACTIVATED, continuity=continuity,
                       authority=TransitionAuthority.INCUMBENT_ONLY, population_known=1000,
                       r_incumbent=r)
        rows.append({"continuity": continuity.value, "r": a.r_incumbent, "q": a.q_independent,
                     "residual_fraction": a.residual_fraction(),
                     "dependent_breakage": a.dependent_breakage()})
    return {"varied": "primary object continuity", "held_constant": "mechanism, authority, N, r, q=0",
            "rows": rows, "statement": "With success fractions fixed, continuity does not "
                    "enter the identity. In real systems it may affect achievable r and q."}


__all__ = ["MechanismSupport", "ObjectContinuity", "TransitionAuthority", "Outcome",
           "Assessment", "authority_effect", "independent_success_effect",
           "continuity_effect", "__version__"]
