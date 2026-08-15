"""Static validation.

Inherits the WhiteCrow ``validate_prompt_bodies.py`` check family and adds the
Workbench-specific ones. Contract drift is classified rather than uniformly
rejected: historical drift already present in a BASELINE is grandfathered as
``KNOWN_BASELINE_DRIFT`` and must not block anything; only drift that a
candidate introduces or increases is fatal (``NEW_CANDIDATE_DRIFT``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import (
    ContractReport,
    DriftClass,
    DriftWaiver,
    PromptAsset,
    PromptVariant,
)


@dataclass
class ValidationIssue:
    code: str
    severity: str            # error | warning | info
    message: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_public(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity,
                "message": self.message, "detail": self.detail}


@dataclass
class ValidationResult:
    verdict: str                       # pass | fail | warn
    drift_class: DriftClass
    issues: list[ValidationIssue]
    contract: ContractReport | None = None
    baseline_contract: ContractReport | None = None

    @property
    def ok(self) -> bool:
        return self.verdict != "fail"

    def to_public(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "drift_class": self.drift_class,
            "issues": [i.to_public() for i in self.issues],
            "contract": self.contract.to_public() if self.contract else None,
            "baseline_contract": (self.baseline_contract.to_public()
                                  if self.baseline_contract else None),
        }


class StaticValidator:
    """Branch-agnostic. Contract facts arrive as ``ContractReport`` objects."""

    def validate(
        self,
        asset: PromptAsset,
        candidate: PromptVariant,
        candidate_contract: ContractReport,
        baseline: PromptVariant | None,
        baseline_contract: ContractReport | None,
        waivers: list[DriftWaiver] | None = None,
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []

        # --- inherited from WhiteCrow validate_prompt_bodies.py ---
        if not candidate.source_text.strip():
            issues.append(ValidationIssue(
                "empty_source", "error", "Исходник пуст"))

        for region in asset.regions:
            if region.locate(candidate.source_text) is None:
                issues.append(ValidationIssue(
                    "region_missing", "error",
                    f"Область «{region.name}» не найдена — маркер удалён",
                    {"region": region.name, "marker": region.start_marker}))

        # --- protected regions must be byte-identical to baseline ---
        # unless the candidate is an explicitly declared contract revision, in
        # which case the drift fingerprint below is the gate instead.
        if baseline is not None:
            for region in asset.regions:
                if region.kind != "protected":
                    continue
                base_txt = region.extract(baseline.source_text)
                cand_txt = region.extract(candidate.source_text)
                if base_txt is None or cand_txt is None:
                    continue
                if base_txt == cand_txt:
                    continue
                if candidate.contract_revision:
                    issues.append(ValidationIssue(
                        "contract_region_revised", "info",
                        f"Защищённая область «{region.name}» изменена как явная "
                        f"ревизия контракта — дрейф проверяется в полную силу",
                        {"region": region.name, "intent": candidate.intent}))
                else:
                    issues.append(ValidationIssue(
                        "protected_region_modified", "error",
                        f"Защищённая область «{region.name}» изменена: {region.reason}",
                        {"region": region.name}))

        # --- invariants must survive verbatim ---
        for inv in asset.invariants:
            if inv and inv not in candidate.source_text:
                issues.append(ValidationIssue(
                    "invariant_lost", "error",
                    "Инвариант ассета отсутствует в тексте",
                    {"invariant": inv[:120]}))

        # --- consumed field never requested is always fatal ---
        if candidate_contract.missing_from_prompt:
            issues.append(ValidationIssue(
                "contract_missing_field", "error",
                "Промпт не запрашивает поля, которые читает потребитель",
                {"fields": candidate_contract.missing_from_prompt}))

        # --- structural drift classification (C1) ---
        drift_class, drift_issues = self._classify_drift(
            candidate, candidate_contract, baseline_contract, waivers or [])
        issues.extend(drift_issues)

        has_error = any(i.severity == "error" for i in issues)
        has_warn = any(i.severity == "warning" for i in issues)
        verdict = "fail" if has_error else ("warn" if has_warn else "pass")

        return ValidationResult(
            verdict=verdict, drift_class=drift_class, issues=issues,
            contract=candidate_contract, baseline_contract=baseline_contract,
        )

    # ------------------------------------------------------------------

    def _classify_drift(
        self,
        candidate: PromptVariant,
        candidate_contract: ContractReport,
        baseline_contract: ContractReport | None,
        waivers: list[DriftWaiver],
    ) -> tuple[DriftClass, list[ValidationIssue]]:
        """Compare defect *identities*, never defect counts.

        Rules:
          * empty candidate fingerprint            -> NONE
          * candidate is the baseline              -> KNOWN_BASELINE_DRIFT
          * candidate ⊆ baseline                   -> KNOWN_BASELINE_DRIFT
          * every new defect explicitly waived     -> WAIVED_CANDIDATE_DRIFT
          * anything else                          -> NEW_CANDIDATE_DRIFT (fatal)
        """
        issues: list[ValidationIssue] = []
        cand_fp = candidate_contract.fingerprint.normalised()

        if cand_fp.is_empty():
            return "NONE", issues

        if candidate.state == "BASELINE" or baseline_contract is None:
            issues.append(ValidationIssue(
                "known_baseline_drift", "info",
                f"Исторический дрейф контракта {candidate_contract.summary()} "
                f"(промпт/объявлено/потребляется) зафиксирован как известный",
                {"fingerprint": cand_fp.to_public()}))
            return "KNOWN_BASELINE_DRIFT", issues

        base_fp = baseline_contract.fingerprint.normalised()
        introduced = cand_fp.difference(base_fp)
        repaired = cand_fp.repaired(base_fp)

        if not introduced:
            issues.append(ValidationIssue(
                "inherited_baseline_drift", "info",
                "Дрейф кандидата — подмножество известного baseline-дрейфа",
                {"candidate_fingerprint": cand_fp.fingerprint_hash(),
                 "baseline_fingerprint": base_fp.fingerprint_hash(),
                 "repaired": sorted(f"{c}:{i}" for c, i in repaired)}))
            return "KNOWN_BASELINE_DRIFT", issues

        waived = {w.key() for w in waivers
                  if w.asset_id in ("*", candidate_contract.asset_id)}
        unwaived = introduced - waived

        if not unwaived:
            issues.append(ValidationIssue(
                "waived_candidate_drift", "warning",
                "Новый дрейф допущен явным waiver с указанием ADR",
                {"waived": sorted(f"{c}:{i}" for c, i in introduced),
                 "waivers": [w.to_public() for w in waivers
                             if w.key() in introduced]}))
            return "WAIVED_CANDIDATE_DRIFT", issues

        issues.append(ValidationIssue(
            "new_candidate_drift", "error",
            "Кандидат вводит дефекты контракта, которых нет в baseline "
            "(одинаковое их количество ничего не доказывает)",
            {"introduced": sorted(f"{c}:{i}" for c, i in unwaived),
             "repaired": sorted(f"{c}:{i}" for c, i in repaired),
             "candidate_fingerprint": cand_fp.fingerprint_hash(),
             "baseline_fingerprint": base_fp.fingerprint_hash(),
             "candidate_total": len(cand_fp.as_set()),
             "baseline_total": len(base_fp.as_set()),
             "note": "counts may be equal; identity is what is compared"}))
        return "NEW_CANDIDATE_DRIFT", issues
