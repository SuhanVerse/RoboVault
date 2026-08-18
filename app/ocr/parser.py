"""Best-effort parser for bill OCR text — returns suggestions, not ground truth."""

import re

LINE_ITEM_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9 _\-/.]{1,60}?)\s+"
    r"(?P<qty>\d+)\s*(?:x|X|pcs|pc|nos)?\s*(?:@\s*)?"
    r"(?P<price>\d+(?:\.\d{1,2})?)\s*(?:rs|npr|\.)?$"
)


def parse_line_items(text: str) -> list[dict[str, str | int | float]]:
    """Best-effort parse of OCR text into {name, quantity, price} suggestions."""
    suggestions = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = LINE_ITEM_RE.match(line)
        if match:
            suggestions.append(
                {
                    "name": match.group("name").strip(),
                    "quantity": int(match.group("qty")),
                    "price": float(match.group("price")),
                }
            )
    return suggestions
