"""QR code renderer for the offline HTML report.

Generates a QR code PNG that encodes ``cvassure:sha256:<payload_sha256>``.
All rendering is done inline — no network call, no CDN.

Requires ``qrcode[pil]``:
    pip install "qrcode[pil]>=7,<9"
"""

from __future__ import annotations

import base64
import io
from pathlib import Path


def _make_qr_image(data: str, box_size: int = 8, border: int = 4):
    """Return a PIL Image of the QR code."""
    try:
        import qrcode  # type: ignore[import]
        from qrcode.constants import ERROR_CORRECT_M  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "qrcode[pil] is required for QR code generation. "
            "Install it with: pip install 'qrcode[pil]>=7,<9'"
        ) from exc

    qr = qrcode.QRCode(
        version=None,  # auto-detect
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1F3864", back_color="white")
    return img


def render_qr(data: str, path: Path, size: int = 256) -> None:
    """Write a QR code PNG to ``path``.

    Args:
        data: The string to encode in the QR code.
        path: Output path for the PNG file.
        size: Target side length in pixels (approximate; box_size is adjusted).
    """
    box_size = max(4, size // 40)
    img = _make_qr_image(data, box_size=box_size)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path), format="PNG")


def render_qr_base64(data: str, size: int = 256) -> str:
    """Return a ``data:image/png;base64,...`` string for inline HTML embedding.

    No file is written. The returned string can be used directly as
    the ``src`` attribute of an ``<img>`` tag.
    """
    box_size = max(4, size // 40)
    img = _make_qr_image(data, box_size=box_size)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def payload_qr_content(payload_sha256: str) -> str:
    """The canonical QR content string for a CVAssure payload hash."""
    return f"cvassure:sha256:{payload_sha256}"
