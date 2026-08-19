"""Image preprocessing helpers for OCR."""

from PIL import Image, ImageEnhance, ImageOps


def preprocess_image(image_path: str) -> Image.Image:
    """Normalize a scanned bill image for OCR (grayscale + contrast)."""
    image = Image.open(image_path).convert("L")
    image = ImageOps.autocontrast(image)
    return ImageEnhance.Contrast(image).enhance(2.0)
