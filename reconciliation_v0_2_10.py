"""v0.2.10 reconciliation primitives.

Pins the authentic recovered v0.2.9 bundle and retains historical transport
decoders for archaeological replay. No publishing or production activation is
performed here.
"""
from __future__ import annotations

import base64
import codecs
import hashlib
import json
import re
from pathlib import Path

RECOVERED_V029_SOURCE_KIND = "google_drive_recovered_bundle"
RECOVERED_V029_DRIVE_FILE_ID = "1a6h9u7JtEYGkbK8nzVE3scClYUvO9E4T"
RECOVERED_V029_ARCHIVE_SHA256 = (
    "a0986c482309b6de7bf1bf90be3db9cba546f4cd0703813fe8b2161508fede7a"
)

# Archaeological transport metadata retained for reproducibility diagnostics.
HISTORICAL_V029_TRANSPORT_REF = "restore/v0.2.9-rot13-transport"
HISTORICAL_V029_TRANSPORT_BLOBS = {
    "chunk_00.rot13": "7dc32d6ac50c502ed6d708512ac84931611cc96d",
    "chunk_01.rot13": "eed6604945d496d49c9387abc2a8f0fde6c578da",
    "part_02.rot13": "83aeee528d3f07f4c69d7cd45f0462d1a39f1b73",
    "part_03.rot13": "9c92d3f9e98e156bc47e41e8b30d35e52e3d1bbe",
}
HISTORICAL_V029_MISSING_FILE_BLOB = (
    "3ea6f1a72e4560baaf035ed6b319d83c1cbe7c32"
)


def _normalized_base64(chunks: list[str] | tuple[str, ...]) -> str:
    if not isinstance(chunks, (list, tuple)) or not chunks:
        raise ValueError("archive_chunks_missing")
    parts: list[str] = []
    for chunk in chunks:
        if not isinstance(chunk, str) or not chunk.strip():
            raise ValueError("archive_chunk_invalid")
        parts.append("".join(chunk.split()))
    encoded = "".join(parts)
    encoded += "=" * (-len(encoded) % 4)
    return encoded


def decode_base64_chunks(chunks: list[str] | tuple[str, ...]) -> bytes:
    """Decode ordered base64 chunks, accepting stripped padding."""
    try:
        return base64.b64decode(_normalized_base64(chunks), validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("archive_transport_invalid") from exc


def decode_rot13_base64_chunks(chunks: list[str] | tuple[str, ...]) -> bytes:
    """Reverse ROT13 text transport, then decode the base64 payload."""
    if not isinstance(chunks, (list, tuple)) or not chunks:
        raise ValueError("archive_chunks_missing")
    normalized: list[str] = []
    for chunk in chunks:
        if not isinstance(chunk, str) or not chunk.strip():
            raise ValueError("archive_chunk_invalid")
        normalized.append(codecs.decode("".join(chunk.split()), "rot_13"))
    return decode_base64_chunks(normalized)


def require_archive_digest(
    payload: bytes,
    expected_sha256: str = RECOVERED_V029_ARCHIVE_SHA256,
) -> bytes:
    """Require exact SHA-256 identity for a recovered archive."""
    if not isinstance(payload, bytes):
        raise ValueError("archive_bytes_invalid")
    if not isinstance(expected_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", expected_sha256
    ):
        raise ValueError("archive_digest_invalid")
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected_sha256:
        raise ValueError("archive_digest_mismatch")
    return payload


def reconstruct_archive(
    chunks: list[str] | tuple[str, ...],
    *,
    expected_sha256: str = RECOVERED_V029_ARCHIVE_SHA256,
) -> bytes:
    """Decode base64 chunks and require an exact payload digest."""
    return require_archive_digest(
        decode_base64_chunks(chunks),
        expected_sha256,
    )


def reconstruct_rot13_archive(
    chunks: list[str] | tuple[str, ...],
    *,
    expected_sha256: str,
) -> bytes:
    """Decode ROT13/base64 chunks and require an exact payload digest."""
    return require_archive_digest(
        decode_rot13_base64_chunks(chunks),
        expected_sha256,
    )


RETIRED_V029_HOLDOUT_SHA256 = (
    "dcff8740576d0fd870078b6c0fca80e4c027cb8efedf997e0d70126315b33af5"
)
PUBLIC_SAFE_JSON_ARTIFACT_COUNT = 26
PUBLIC_SAFE_FREEZE_FILE_COUNT = 11


def verify_public_safe_recovered_tree(root: str | Path) -> dict:
    """Verify the publishable recovered v0.2.9 tree without blind holdout bytes.

    This contract intentionally validates only public-safe invariants. The
    retired holdout digest may remain as metadata in the freeze manifest, but
    the holdout content itself must not be present in the promotable tree.
    """
    root = Path(root)
    reasons: list[str] = []
    if not root.is_dir():
        return {
            "valid": False,
            "reasons": ["recovered_tree_missing"],
            "json_artifacts": 0,
            "freeze_files_checked": 0,
            "holdout_present": False,
        }

    holdout_path = root / "blind_holdout_v0_2_9.json"
    holdout_present = holdout_path.exists()
    if holdout_present:
        reasons.append("blind_holdout_present")

    if any(root.glob("*.zip")):
        reasons.append("recovered_archive_present")

    json_paths = sorted(root.glob("*.json"))
    for path in json_paths:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            reasons.append(f"json_invalid:{path.name}")
    if len(json_paths) != PUBLIC_SAFE_JSON_ARTIFACT_COUNT:
        reasons.append(
            f"json_artifact_count_mismatch:{len(json_paths)}"
        )

    manifest_path = root / "FREEZE_MANIFEST_v0_2_9.json"
    checked = 0
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = manifest["files"]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError):
        reasons.append("freeze_manifest_unavailable")
        files = {}

    if files:
        if files.get("blind_holdout_v0_2_9.json") != RETIRED_V029_HOLDOUT_SHA256:
            reasons.append("retired_holdout_hash_metadata_mismatch")
        for name, expected in files.items():
            if name == "blind_holdout_v0_2_9.json":
                continue
            path = root / name
            try:
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                reasons.append(f"freeze_file_missing:{name}")
                continue
            if actual != expected:
                reasons.append(f"freeze_drift:{name}")
                continue
            checked += 1
        if checked != PUBLIC_SAFE_FREEZE_FILE_COUNT:
            reasons.append(f"freeze_file_count_mismatch:{checked}")

    return {
        "valid": not reasons,
        "reasons": reasons,
        "json_artifacts": len(json_paths),
        "freeze_files_checked": checked,
        "holdout_present": holdout_present,
    }
