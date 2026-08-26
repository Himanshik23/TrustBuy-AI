"""Image-based product analysis (Feature: "Image-Based Product Analysis").

Real OCR (Tesseract, via `pytesseract` - the exact same library and call
pattern already used and verified in `community-service/app/ocr.py`) plus
honest, pattern-based field parsing over the extracted text - the same
"only ever report what a regex genuinely matched" discipline the marketplace
adapters already follow (see `app/adapters/generic.py`'s `_detect_urgency`,
`_detect_sale_context`, `_detect_business_registration`). Nothing here uses
a trained vision/OCR-understanding model, and nothing here guesses a field
it could not actually find text for - an unmatched field is `None`
("unavailable"), never invented.

What this module deliberately does NOT claim to do: recognize a product by
its visual appearance (no product-recognition model is used - "Nike Air
Max" is only identified if the words "Nike" and "Air Max" literally appear
as text in the image), detect a specifically *edited* pixel region (real
forensic tamper detection - error-level analysis, noise-inconsistency
mapping - is a distinct, more specialized capability this module does not
implement), or reverse-image-search the wider internet. The one real
image-vs-image signal implemented is exact-content perceptual-hash reuse
detection *among images previously uploaded to TrustBuy itself* via this
same feature (`ProductImage.perceptual_hash`) - genuinely working, but
narrower than "has this image been used anywhere online," which this
module does not attempt.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field

from trustbuy_agent_sdk import Evidence, Polarity

logger = logging.getLogger(__name__)

_OCR_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

MIN_USABLE_TEXT_LENGTH = 12  # below this, OCR is treated as having found nothing usable


def extract_text_from_image(content: bytes, content_type: str) -> str | None:
    """Real Tesseract OCR - identical approach to community-service's own
    `app/ocr.py`, kept as a separate copy here (not a shared lib import)
    because catalog-service and community-service are independently
    deployable and neither should hard-depend on the other's image stack."""
    if content_type not in _OCR_CONTENT_TYPES:
        return None
    try:
        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(content))
        text = pytesseract.image_to_string(image)
        text = text.strip()
        return text or None
    except Exception:
        logger.exception("Image OCR failed - continuing without extracted text.")
        return None


def compute_average_hash(content: bytes) -> str | None:
    """A real, standard 64-bit average-hash (aHash): shrink to 8x8
    grayscale, hash bit i = 1 if pixel i is >= the block's own mean
    brightness. Two images that are the same photo (even re-compressed or
    lightly resized) hash identically or near-identically; this is the
    well-known, genuinely-working algorithm behind "has this exact photo
    been used before," not a fabricated capability. Returned as 16 hex
    characters, matching `product_images.perceptual_hash`."""
    try:
        from PIL import Image

        image = Image.open(io.BytesIO(content)).convert("L").resize((8, 8), Image.LANCZOS)
        pixels = list(image.getdata())
        avg = sum(pixels) / len(pixels)
        bits = "".join("1" if p >= avg else "0" for p in pixels)
        return f"{int(bits, 2):016x}"
    except Exception:
        logger.exception("Perceptual hash computation failed.")
        return None


def hamming_distance(hash_a: str, hash_b: str) -> int | None:
    try:
        return bin(int(hash_a, 16) ^ int(hash_b, 16)).count("1")
    except (ValueError, TypeError):
        return None


@dataclass
class ParsedImageFields:
    product_name: str | None = None
    product_name_confidence: str | None = None  # "low" | "medium" - never "high": OCR text-position heuristic only
    brand: str | None = None
    price: float | None = None
    currency: str | None = None
    discount_percent: float | None = None
    seller_name: str | None = None
    platform_hint: str | None = None
    model_sku: str | None = None
    warranty_mentioned: bool = False
    contact_info_present: bool = False
    rating_text: str | None = None
    promotional_claims: list[str] = field(default_factory=list)
    raw_text: str | None = None

    def has_any_field(self) -> bool:
        return bool(
            self.product_name
            or self.price is not None
            or self.seller_name
            or self.brand
            or self.model_sku
        )


_PRICE_RE = re.compile(r"(?:₹|Rs\.?|INR|\$|USD)\s?([\d][\d,]*(?:\.\d{1,2})?)")
_DISCOUNT_RE = re.compile(r"(\d{1,3})\s?%\s*(?:off|OFF|discount|Off)")
_SELLER_RE = re.compile(
    r"(?:sold\s+by|seller\s*[:\-]|store\s*[:\-]|shop\s*[:\-])\s*([A-Za-z0-9][\w &.'\-]{1,60})", re.IGNORECASE
)
_BRAND_RE = re.compile(r"brand\s*[:\-]\s*([A-Za-z0-9][\w &.'\-]{1,40})", re.IGNORECASE)
_MODEL_RE = re.compile(r"(?:model|sku|item\s*(?:no|number)?)\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9\-/]{3,20})", re.IGNORECASE)
_RATING_RE = re.compile(r"(\d(?:\.\d)?)\s*(?:/|out of)\s*5")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{3,5}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}")
_WARRANTY_RE = re.compile(r"warrant(?:y|ies)|guarantee", re.IGNORECASE)
# Category breadcrumb nav (e.g. "Home & Kitchen > Air Conditioners » Split-
# System Air Conditioners", "Electronics / Mobiles / Smartphones") - common
# above the actual title in marketplace screenshots, and OCRs as an
# innocuous-looking text line that would otherwise pass as a title candidate.
_BREADCRUMB_RE = re.compile(r"\s[>»›]\s")
_PROMO_PHRASES = [
    "limited time", "hurry", "flash sale", "deal of the day", "offer ends", "buy now",
    "only today", "sale ends", "clearance", "% off", "special offer", "exclusive deal",
]
_PLATFORM_HINTS = {
    "amazon": "amazon_in", "flipkart": "flipkart", "myntra": "myntra", "meesho": "meesho",
    "instagram": "instagram_shopping", "facebook": "facebook_marketplace", "whatsapp": "unclassified",
}


def parse_fields_from_text(text: str | None) -> ParsedImageFields:
    """Pattern-based extraction only - every field is either a real regex
    match against the OCR'd text or `None`. No field is inferred, guessed,
    or filled from anything other than text that genuinely appears in the
    image (ADR-004)."""
    fields = ParsedImageFields(raw_text=text)
    if not text or len(text) < MIN_USABLE_TEXT_LENGTH:
        return fields

    lower = text.lower()

    price_match = _PRICE_RE.search(text)
    if price_match:
        try:
            fields.price = float(price_match.group(1).replace(",", ""))
            fields.currency = "INR" if any(sym in text for sym in ("₹", "Rs", "INR")) else "USD"
        except ValueError:
            pass

    discount_match = _DISCOUNT_RE.search(text)
    if discount_match:
        try:
            fields.discount_percent = float(discount_match.group(1))
        except ValueError:
            pass

    seller_match = _SELLER_RE.search(text)
    if seller_match:
        fields.seller_name = seller_match.group(1).strip()

    brand_match = _BRAND_RE.search(text)
    if brand_match:
        fields.brand = brand_match.group(1).strip()

    model_match = _MODEL_RE.search(text)
    if model_match:
        fields.model_sku = model_match.group(1).strip()

    rating_match = _RATING_RE.search(text)
    if rating_match:
        fields.rating_text = f"{rating_match.group(1)} out of 5"

    fields.warranty_mentioned = bool(_WARRANTY_RE.search(text))
    fields.contact_info_present = bool(_EMAIL_RE.search(text) or _PHONE_RE.search(text))
    fields.promotional_claims = [phrase for phrase in _PROMO_PHRASES if phrase in lower]

    for hint, platform in _PLATFORM_HINTS.items():
        if hint in lower:
            fields.platform_hint = platform
            break

    # Product name: best-effort only, explicitly marked low-confidence -
    # pytesseract's plain-text output carries no font-size/position data,
    # so there is no reliable way to know which line is really the title.
    # Heuristic: the FIRST line that is mostly letters, was not already
    # claimed by a more specific field above, and isn't a warranty/rating/
    # promo/breadcrumb line - product titles are near-universally the first
    # PRODUCT text block in a real listing screenshot, but real marketplace
    # screenshots (Amazon, Flipkart, ...) usually show a category breadcrumb
    # nav bar (e.g. "Home & Kitchen > Air Conditioners > ...") above the
    # actual title, which OCRs as plain text just like a title would - so
    # breadcrumb-shaped lines are excluded rather than trusted as "first".
    claimed = {v for v in (fields.seller_name, fields.brand, fields.model_sku) if v}
    candidates = [
        line.strip()
        for line in text.splitlines()
        if len(line.strip()) >= 8
        and sum(c.isalpha() for c in line) / max(len(line), 1) > 0.5
        and line.strip() not in claimed
        and not _PRICE_RE.search(line)
        and not _SELLER_RE.search(line)
        and not _WARRANTY_RE.search(line)
        and not _RATING_RE.search(line)
        and not _DISCOUNT_RE.search(line)
        and not _BREADCRUMB_RE.search(line)
        and not any(phrase in line.lower() for phrase in _PROMO_PHRASES)
    ]
    if candidates:
        fields.product_name = candidates[0][:200]
        fields.product_name_confidence = "low"

    return fields


def build_extracted_fields_summary(fields: ParsedImageFields) -> dict:
    """The honest, UI-facing shape: every field either a real extracted
    value or the string 'unavailable' - never silently omitted, so the
    user can see exactly what could and could not be read from their image."""
    def _or_unavailable(value):
        return value if value not in (None, "", []) else "unavailable"

    return {
        "product_name": _or_unavailable(fields.product_name),
        "product_name_confidence": fields.product_name_confidence or "unavailable",
        "brand": _or_unavailable(fields.brand),
        "price": fields.price if fields.price is not None else "unavailable",
        "currency": _or_unavailable(fields.currency),
        "discount_percent": fields.discount_percent if fields.discount_percent is not None else "unavailable",
        "seller_name": _or_unavailable(fields.seller_name),
        "platform_hint": _or_unavailable(fields.platform_hint),
        "model_sku": _or_unavailable(fields.model_sku),
        "warranty_mentioned": fields.warranty_mentioned,
        "contact_info_present": fields.contact_info_present,
        "rating_text": _or_unavailable(fields.rating_text),
        "promotional_claims": fields.promotional_claims,
        "ocr_text_excerpt": (fields.raw_text or "")[:800] or "unavailable",
    }


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _names_conflict(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return False
    shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
    # Real substring/token-overlap check, not a fuzzy-match guess: if
    # neither string contains a meaningful chunk of the other, call it a
    # conflict rather than silently assuming they refer to the same thing.
    return shorter not in longer and not _token_overlap(a, b)


def _token_overlap(a: str, b: str) -> bool:
    tokens_a = {t for t in re.findall(r"[a-z0-9]+", a.lower()) if len(t) > 2}
    tokens_b = {t for t in re.findall(r"[a-z0-9]+", b.lower()) if len(t) > 2}
    if not tokens_a or not tokens_b:
        return False
    overlap = tokens_a & tokens_b
    return len(overlap) / min(len(tokens_a), len(tokens_b)) >= 0.5


def cross_check(
    image_fields: ParsedImageFields,
    *,
    fetched_title: str | None,
    fetched_seller: str | None,
    fetched_brand: str | None,
    fetched_price: float | None,
) -> tuple[list[str], list[Evidence]]:
    """Compares image-derived fields against an independently-fetched
    extraction. Never silently prefers one source: every real difference
    is surfaced as an explicit conflict description AND fed into evidence
    as its own item (ADR-004/ADR-007) - agreement is rewarded with a small
    SUPPORTS item (corroboration), a real conflict with a CONTRADICTS item,
    and anything neither side could compare is left alone rather than
    guessed at."""
    conflicts: list[str] = []
    evidence: list[Evidence] = []

    if image_fields.product_name and fetched_title and _names_conflict(image_fields.product_name, fetched_title):
        conflicts.append(
            f"Product name differs: image shows \"{image_fields.product_name}\", "
            f"the listing page shows \"{fetched_title}\"."
        )
    if image_fields.seller_name and fetched_seller and _names_conflict(image_fields.seller_name, fetched_seller):
        conflicts.append(
            f"Seller name differs: image shows \"{image_fields.seller_name}\", "
            f"the listing page shows \"{fetched_seller}\"."
        )
    if image_fields.brand and fetched_brand and _names_conflict(image_fields.brand, fetched_brand):
        conflicts.append(f"Brand differs: image shows \"{image_fields.brand}\", the listing page shows \"{fetched_brand}\".")
    if image_fields.price is not None and fetched_price is not None:
        # A genuine mismatch, not float noise - tolerate small rounding/
        # currency-display differences before calling it a conflict.
        if fetched_price > 0 and abs(image_fields.price - fetched_price) / fetched_price > 0.08:
            conflicts.append(
                f"Price differs: image shows {image_fields.price}, the listing page shows {fetched_price}."
            )

    if conflicts:
        evidence.append(
            Evidence(
                polarity=Polarity.CONTRADICTS,
                weight=0.6,
                summary="Information conflict detected between the uploaded image and the fetched listing page: "
                + " ".join(conflicts),
                detail={"conflicts": conflicts},
            )
        )
    else:
        compared_fields = sum(
            1
            for pair in (
                (image_fields.product_name, fetched_title),
                (image_fields.seller_name, fetched_seller),
                (image_fields.brand, fetched_brand),
                (image_fields.price, fetched_price),
            )
            if pair[0] is not None and pair[1] is not None
        )
        if compared_fields > 0:
            evidence.append(
                Evidence(
                    polarity=Polarity.SUPPORTS,
                    weight=min(0.5, 0.15 * compared_fields),
                    summary=f"Uploaded image is consistent with the fetched listing page on {compared_fields} "
                    "compared field(s) - no conflicting information detected.",
                    detail={"compared_fields": compared_fields},
                )
            )

    return conflicts, evidence


def compute_investigation_confidence(
    *,
    sources_used: int,
    conflicts_found: int,
    agents_completed: int,
    agents_total: int,
    ocr_text_length: int,
    had_image: bool,
) -> tuple[str, str]:
    """Deterministic, rule-based confidence tier over how much reliable
    evidence actually went into this investigation - not a model's
    self-reported certainty, and never allowed to read HIGH when evidence
    is thin (Feature requirement: "never use a high confidence score when
    evidence is incomplete")."""
    coverage = agents_completed / agents_total if agents_total else 0.0

    if conflicts_found > 0:
        return (
            "LOW",
            "Information conflict detected between the sources used for this investigation - "
            "treat the recommendation as provisional until the discrepancy is resolved.",
        )
    if had_image and ocr_text_length < MIN_USABLE_TEXT_LENGTH:
        return ("LOW", "Only limited information could be extracted from the uploaded image.")
    if sources_used >= 2 and coverage >= 0.6:
        return (
            "HIGH",
            "Product, seller, and pricing information were corroborated across multiple independent sources, "
            "and most intelligence agents returned usable evidence.",
        )
    if sources_used >= 1 and coverage >= 0.4:
        return (
            "MEDIUM",
            "A reasonable amount of evidence was available, but it came from a single source or only some "
            "intelligence agents returned usable evidence.",
        )
    return (
        "LOW",
        "Little independently verifiable evidence was available for this investigation - "
        "treat the recommendation as provisional.",
    )
