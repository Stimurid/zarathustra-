"""A14 follow-up: mirror the ONE prompt body the G-S24 bindings actually point at.

Provenance, not authorship. The file is owned by LOCAL_SOCRATES; this verifies a
read-only copy in our mirror and records exactly what can and cannot be claimed
about it. It is deliberately NOT registered as an editable PromptAsset:
rewriting a body that no runtime consumes would be a claim we cannot back.

Source: Drive 1FRmTQfj2Vxwmgde_C_u2zX1fbGISGLUL
        prompts/MODE_AND_REFLEXIVITY_GOVERNOR_PROMPT_PACK.md
        text/markdown, owner timurid@gmail.com, 1844 bytes

FIDELITY: the transport for this file was a base64 payload transcribed by hand,
and the first attempt silently altered one word. That is why the size assertion
below exists and why the mirror labels this file BYTE_EXACT_UNVERIFIED rather
than BYTE_EXACT: the owner's G-S24_SHA256SUMS does not list this file at all
(defect SD-002), so there is no authority to check the hash against. Size and
content were cross-checked against two independent Drive reads.

Run: python scripts/socrates_mirror_add_prompt_pack.py
"""
from __future__ import annotations

import base64
import hashlib
import sys
from pathlib import Path

MIRROR = Path(__file__).resolve().parents[1] / "socrates_mirror"
MD = MIRROR / "prompts" / "MODE_AND_REFLEXIVITY_GOVERNOR_PROMPT_PACK.md"
RAW = MIRROR / "_raw" / "MODE_AND_REFLEXIVITY_GOVERNOR_PROMPT_PACK.md.b64"

#: Drive's own metadata for the file. A mismatch means the mirror holds
#: something other than what the owner holds.
OWNER_REPORTED_SIZE = 1844

#: Phrases the two independent Drive reads (metadata snippet + download) agree
#: on. They are the anchors a transcription slip would break.
ANCHORS = (
    "Stop escalating when another level adds no plausible discriminating effect.",
    "Never infer truth from vote count.",
    "Default persona selection is `NO_PERSONA`.",
    "Never write durable state merely because an arbitration concluded.",
)


def main() -> int:
    if not MD.exists():
        print(f"missing {MD}", file=sys.stderr)
        return 1
    data = MD.read_bytes().replace(b"\r\n", b"\n")
    if len(data) != OWNER_REPORTED_SIZE:
        print(f"size mismatch: {len(data)} != {OWNER_REPORTED_SIZE} — the mirror "
              "does not hold the owner's file", file=sys.stderr)
        return 1
    text = data.decode("utf-8")
    for anchor in ANCHORS:
        if anchor not in text:
            print(f"anchor missing: {anchor!r}", file=sys.stderr)
            return 1
    MD.write_bytes(data)                      # normalise line endings in place
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_text(base64.b64encode(data).decode("ascii"), encoding="ascii")
    print(f"verified {MD} ({len(data)} bytes, {len(ANCHORS)} anchors)")
    print(f"sha256 {hashlib.sha256(data).hexdigest()}")
    print("owner manifest entry: ABSENT (defect SD-002) — no authority to "
          "verify the hash against")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
