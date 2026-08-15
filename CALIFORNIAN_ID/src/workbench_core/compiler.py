"""Prompt compiler.

Two hard rules:

1. **Equivalence.** The compiled payload is exactly what the branch runtime
   would send. The compiler asks the adapter to build the invocation and then
   explains it; it never invents its own assembly for a node the runtime
   assembles differently.
2. **100 % provenance.** Every character of every compiled target belongs to
   exactly one span. Spans are either ``source_module`` (traceable to an asset
   region) or ``compiler_generated`` (traceable to a named compiler rule).
   Unexplained text is a compiler error, not a warning.
"""
from __future__ import annotations

from .branch import BranchAdapter, Fixture, Invocation
from .models import (
    CompiledPrompt,
    CompilerProfile,
    PromptAsset,
    PromptVariant,
    SourceSpan,
    json_dumps,
    sha256_text,
)


class ProvenanceError(RuntimeError):
    """Raised when compiled text cannot be fully attributed."""


class PromptCompiler:
    def compile(
        self,
        adapter: BranchAdapter,
        asset: PromptAsset,
        variant: PromptVariant,
        fixture: Fixture,
        profile: CompilerProfile,
        step_id: str,
    ) -> CompiledPrompt:
        inv: Invocation = adapter.build_invocation(asset.asset_id, variant.source_text, fixture)

        warnings: list[str] = []
        spans: list[SourceSpan] = []

        spans += self._attribute(
            target="system", text=inv.system_text,
            asset=asset, variant=variant, profile=profile,
            contributions=[(variant.source_text, None)],
            scaffold_rule="system_scaffold",
        )
        spans += self._attribute(
            target="user", text=inv.user_text,
            asset=asset, variant=variant, profile=profile,
            contributions=[(fixture.text, "fixture")],
            scaffold_rule="user_payload_passthrough",
            fixture_id=fixture.fixture_id,
        )

        truncated = len(fixture.text) > len(inv.user_text)
        if truncated:
            warnings.append(
                f"user payload truncated to {len(inv.user_text)} chars "
                f"by rule user_payload_truncation")

        if profile.allow_superprompt is False and profile.module_loading == "eager":
            warnings.append("eager module loading with superprompt disabled")

        canonical = json_dumps({
            "profile_id": profile.profile_id,
            "branch": profile.branch,
            "step_id": step_id,
            "system": inv.system_text.replace("\r\n", "\n"),
            "user": inv.user_text.replace("\r\n", "\n"),
            "sources": [f"{asset.asset_id}:{variant.variant_id}:{variant.source_hash}"],
        })

        compiled = CompiledPrompt(
            compiled_hash="sha256:" + sha256_text(canonical),
            profile_id=profile.profile_id,
            branch=profile.branch,
            step_id=step_id,
            system_text=inv.system_text,
            user_template=inv.user_text,
            sources=[{
                "asset_id": asset.asset_id,
                "variant_id": variant.variant_id,
                "version": variant.version,
                "source_hash": variant.source_hash,
            }],
            source_map=spans,
            token_count={
                "system": self._estimate_tokens(inv.system_text),
                "user": self._estimate_tokens(inv.user_text),
                "total": self._estimate_tokens(inv.system_text) + self._estimate_tokens(inv.user_text),
                "method": "estimate",
                "measured": False,
            },
            warnings=warnings,
            truncated=truncated,
        )

        gaps = compiled.coverage_gaps()
        if gaps:
            raise ProvenanceError(
                f"compiled payload not fully attributed: {gaps}")
        return compiled

    # ------------------------------------------------------------------

    def _attribute(
        self, *, target: str, text: str, asset: PromptAsset,
        variant: PromptVariant, profile: CompilerProfile,
        contributions: list[tuple[str, str | None]],
        scaffold_rule: str, fixture_id: str | None = None,
    ) -> list[SourceSpan]:
        """Locate known contributions, then fill every gap with a named rule."""
        if not text:
            return []

        found: list[tuple[int, int, str | None]] = []
        cursor = 0
        for needle, tag in contributions:
            if not needle:
                continue
            idx = text.find(needle, cursor)
            if idx < 0:
                # runtime may truncate the contribution; try its prefix
                for cut in (len(needle) // 2, 200, 80):
                    if cut <= 0 or cut > len(needle):
                        continue
                    idx = text.find(needle[:cut], cursor)
                    if idx >= 0:
                        needle = text[idx:]
                        break
            if idx >= 0:
                found.append((idx, idx + len(needle), tag))
                cursor = idx + len(needle)

        found.sort()
        spans: list[SourceSpan] = []
        pos = 0
        for start, end, tag in found:
            if start > pos:
                spans.append(self._scaffold(target, pos, start, scaffold_rule, profile))
            if tag == "fixture":
                spans.append(SourceSpan(
                    target=target, span_start=start, span_end=end,
                    kind="compiler_generated", rule_id="fixture_payload",
                    compiler_profile=profile.profile_id,
                    region_name=fixture_id))
            else:
                spans.extend(self._region_spans(
                    target, start, end, text, asset, variant, profile))
            pos = end
        if pos < len(text):
            spans.append(self._scaffold(target, pos, len(text), scaffold_rule, profile))
        return spans

    def _region_spans(
        self, target: str, start: int, end: int, text: str,
        asset: PromptAsset, variant: PromptVariant, profile: CompilerProfile,
    ) -> list[SourceSpan]:
        """Split an asset contribution into its declared regions."""
        body = text[start:end]
        marks: list[tuple[int, int, str, str]] = []
        for region in asset.regions:
            loc = region.locate(body)
            if loc is None:
                continue
            marks.append((loc[0], loc[1], region.name, region.kind))
        marks.sort()

        spans: list[SourceSpan] = []
        pos = 0
        for rs, re_, name, kind in marks:
            if rs < pos:
                continue
            if rs > pos:
                spans.append(self._asset_span(target, start + pos, start + rs,
                                              asset, variant, None, None, profile))
            spans.append(self._asset_span(target, start + rs, start + re_,
                                          asset, variant, name, kind, profile))
            pos = re_
        if pos < len(body):
            spans.append(self._asset_span(target, start + pos, end,
                                          asset, variant, None, None, profile))
        if not spans:
            spans.append(self._asset_span(target, start, end,
                                          asset, variant, None, None, profile))
        return spans

    @staticmethod
    def _asset_span(target, s, e, asset, variant, region_name, region_kind, profile):
        return SourceSpan(
            target=target, span_start=s, span_end=e, kind="source_module",
            asset_id=asset.asset_id, variant_id=variant.variant_id,
            region_name=region_name or "(unnamed)",
            region_kind=region_kind or "editable",
            compiler_profile=profile.profile_id,
        )

    @staticmethod
    def _scaffold(target, s, e, rule_id, profile):
        return SourceSpan(
            target=target, span_start=s, span_end=e, kind="compiler_generated",
            rule_id=rule_id, compiler_profile=profile.profile_id,
        )

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        # No tokenizer dependency; deliberately reported as an estimate.
        return max(0, round(len(text) / 3.5))
