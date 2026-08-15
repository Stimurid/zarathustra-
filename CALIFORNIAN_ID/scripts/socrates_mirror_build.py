"""Decode the byte-exact Socrates G-S24 mirror files and verify them.

The mirror is a READ-ONLY projection cache. Source of truth stays on Google
Drive under LOCAL_SOCRATES ownership. Verification is against the owner's own
`G-S24_SHA256SUMS`, not against a hash we invented.

    python scripts/socrates_mirror_build.py
"""
from __future__ import annotations

import base64
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIRROR = ROOT / "socrates_mirror"
RAW = MIRROR / "_raw"

#: Authoritative hashes copied from the owner's G-S24_SHA256SUMS
#: (Drive id 1p-a9C5kiRsYQRrGurK6_GhaDrmBbed_y).
OWNER_SHA256 = {
    "pipeline.yaml": "9857ff196feb8d57bf61288bd83528d62d520fb1ae4a92a39154bf1a54eb7783",
    "manifest.yaml": "ab3be48060f99973105625c7cc0a90ae7f54a7c7a57d96bbd8425d3ab5443f5c",
    "state_model.yaml": "6ac42305ea55328429ca23e266ba10d6d455639a9d52a0873bd71fa4084638cd",
    "README.md": "51788464b4a80392eea2cda06ae636322feaba1fa21e13d1372bc946a2aaf1e0",
    "prompts/prompt_bindings_v0.3.yaml":
        "6e36e1d12de755d366a9c79a024d01bd5f0e91069d38406dd0001fd9a2e0c875",
}


def main() -> int:
    if not RAW.exists():
        print("no _raw payloads to decode")
        return 0
    report: list[tuple[str, str, str]] = []
    for b64_path in sorted(RAW.glob("*.b64")):
        name = b64_path.name[: -len(".b64")]
        data = base64.b64decode(b64_path.read_text(encoding="utf-8").strip())
        out = MIRROR / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        expected = OWNER_SHA256.get(name)
        status = ("BYTE_EXACT_VERIFIED" if expected and digest == expected
                  else "HASH_MISMATCH" if expected else "NO_OWNER_HASH")
        report.append((name, digest, status))
        print(f"  {status:<20} {name}  {digest[:16]}")
    bad = [r for r in report if r[2] == "HASH_MISMATCH"]
    if bad:
        print(f"\n{len(bad)} file(s) do not match the owner manifest")
        return 1
    print(f"\n{len(report)} file(s) mirrored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
