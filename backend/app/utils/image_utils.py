"""Image helpers shared by the upload route and the vision service."""

import hashlib
import io
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SUPPORTED_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}

MIME_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

# Gemini Flash accepts large images, but downscaling cuts latency and tokens.
MAX_VISION_DIMENSION = 1600


class ImageValidationError(ValueError):
    """Raised when an uploaded file is not a usable label image."""


def sha256_of_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_of_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mime_type_for(path: str | Path) -> str:
    return MIME_BY_EXTENSION.get(Path(path).suffix.lower(), "image/jpeg")


def validate_image_bytes(content: bytes) -> tuple[int, int]:
    """Ensure the payload really is a decodable image; return (width, height)."""
    if not content:
        raise ImageValidationError("The uploaded file is empty")
    try:
        with Image.open(io.BytesIO(content)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(content)) as image:
            return image.size
    except ImageValidationError:
        raise
    except Exception as exc:  # noqa: BLE001 - Pillow raises many subclasses
        raise ImageValidationError(f"Could not read the image: {exc}") from exc


def prepare_for_vision(path: str | Path) -> bytes:
    """Return JPEG bytes capped at MAX_VISION_DIMENSION on the long edge."""
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        width, height = image.size
        longest = max(width, height)
        if longest > MAX_VISION_DIMENSION:
            scale = MAX_VISION_DIMENSION / longest
            image = image.resize(
                (max(1, int(width * scale)), max(1, int(height * scale))),
                Image.LANCZOS,
            )
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=88, optimize=True)
        return buffer.getvalue()


def prepare_for_ocr(path: str | Path, upscale_to: int = 2200) -> Image.Image:
    """Grayscale, denoise and upscale so Tesseract can read small print."""
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("L")
        width, height = image.size
        longest = max(width, height)
        if longest < upscale_to:
            scale = upscale_to / longest
            image = image.resize(
                (int(width * scale), int(height * scale)), Image.LANCZOS
            )
        image = ImageOps.autocontrast(image, cutoff=1)
        image = image.filter(ImageFilter.SHARPEN)
        image = ImageEnhance.Contrast(image).enhance(1.6)
        # Adaptive-ish binarisation: Tesseract prefers dark text on light paper.
        image = image.point(lambda pixel: 255 if pixel > 145 else 0)
        return image
