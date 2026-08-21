"""
extractor.py
------------
The extraction agent. Input per SKU is deliberately tiny:
    Mfg_Part_Num, Part_Desc, E1_Brand, Unilog_Brand, DIB_Brand, Part_Manuf

That's the "limited inputs" case from the problem statement — no PDF, no
image, just a terse free-text description and a manufacturer name. The agent's
job is to turn that into a structured, classified, attribute-rich record.

Two modes:
  - LLM mode (ANTHROPIC_API_KEY set): calls Claude to classify + extract.
  - Heuristic fallback (no API key): rule-based parsing so the pipeline is
    runnable and demoable with zero external dependencies / offline.

Every field returned carries a `confidence` and a `source` string so the
review UI / output sidecar can show provenance instead of a silent guess.
"""

from __future__ import annotations
import json
import os
import re
from dataclasses import dataclass, field


ANTHROPIC_MODEL = "claude-sonnet-4-6"

EXTRACTION_SYSTEM_PROMPT = """You are a product data extraction agent for an industrial/hardware catalog.
You receive only a manufacturer part number, a terse internal description, and a supplier name — no datasheet, no image.
Your job: infer a clean, structured product record from that limited text, and be explicit about what's a direct read vs an inference.

Return ONLY valid JSON (no markdown fences, no commentary) matching this schema:
{
  "manufacturer_name": string,          // best-guess real manufacturer/brand, cleaned up (e.g. "3M", "Diablo", "Freud")
  "brand_name": string,                 // consumer-facing brand if different from manufacturer, else same as manufacturer_name
  "dept": string,                       // top-level department, e.g. "Tools & Equipment", "Fasteners", "Safety"
  "class": string,                      // mid-level class, e.g. "Abrasives", "Power Tool Accessories"
  "fine": string,                       // fine-grained subclass, e.g. "Sanding Discs", "Sanding Belts"
  "classpath": string,                  // "Dept>Class>Fine" joined with '>'
  "product_name": string,               // short canonical product name, 3-8 words
  "short_desc": string,                 // <= 100 chars, human readable
  "long_desc": string,                  // 1-2 sentences, human readable, no marketing fluff
  "features": [string, ...],            // up to 8 short bullet-style feature strings, only if actually implied by the text
  "attributes": [                       // up to 15 structured attributes actually supported by the input text
    {"label": string, "value": string, "uom": string, "confidence": number, "source": string}
  ],
  "overall_confidence": number          // 0-1, your confidence in the record as a whole
}

Rules:
- Never invent numeric specs (voltage, dimensions, certifications) that aren't implied by the input text. If unknown, omit the attribute entirely rather than guessing.
- confidence should reflect how directly the input text supports the value (1.0 = literally stated, 0.5 = plausible inference from brand/product-line knowledge, lower = weak guess).
- source should say where the value came from, e.g. "Part_Desc literal", "inferred from product line naming convention", "inferred from manufacturer catalog knowledge".
- Keep JSON compact. No trailing commentary.
"""


@dataclass
class ExtractionResult:
    raw: dict
    mode: str  # "llm" or "heuristic"


def _clean_manufacturer(part_manuf: str) -> str:
    """'Freud Inc (2435)' -> 'Freud Inc'"""
    if not part_manuf:
        return ""
    return re.sub(r"\s*\([^)]*\)\s*$", "", part_manuf).strip()


def _heuristic_extract(mfg_part_num: str, part_desc: str, part_manuf: str) -> dict:
    """Zero-dependency fallback extractor: regex/keyword parsing only.
    Deliberately conservative — low confidence, no invented specs."""
    manuf_clean = _clean_manufacturer(part_manuf)
    desc = part_desc or ""

    # crude size / grit / count parsing common in this dataset (abrasives-heavy sample)
    attrs = []

    size_match = re.search(r'(\d+(?:\.\d+)?)\s*"?\s*[xX×]\s*(\d+(?:\.\d+)?)\s*"', desc)
    if size_match:
        attrs.append({
            "label": "Size", "value": f'{size_match.group(1)}" x {size_match.group(2)}"',
            "uom": "in", "confidence": 0.9, "source": "Part_Desc literal (regex size match)",
        })

    grit_match = re.search(r'\bP(\d{2,4})\b', desc)
    if grit_match:
        attrs.append({
            "label": "Grit", "value": grit_match.group(1),
            "uom": "", "confidence": 0.9, "source": "Part_Desc literal (grit code)",
        })

    pack_match = re.search(r'(\d+)\s*(?:pc|pk|pack|/box|per box|ct)\b', desc, re.IGNORECASE)
    if pack_match:
        attrs.append({
            "label": "Pack Quantity", "value": pack_match.group(1),
            "uom": "ea", "confidence": 0.85, "source": "Part_Desc literal (pack qty match)",
        })

    dept, cls, fine = "Uncategorized", "Uncategorized", "Uncategorized"
    lower = desc.lower()
    if any(k in lower for k in ["sand", "disc", "belt", "grit", "abrasive"]):
        dept, cls, fine = "Tools & Equipment", "Abrasives", "Sanding Products"
    elif any(k in lower for k in ["dishwasher", "refrigerator", "range", "oven"]):
        dept, cls, fine = "Appliances", "Large Appliances", "Kitchen Appliances"

    return {
        "manufacturer_name": manuf_clean,
        "brand_name": manuf_clean,
        "dept": dept, "class": cls, "fine": fine,
        "classpath": f"{dept}>{cls}>{fine}",
        "product_name": desc[:60].strip(),
        "short_desc": desc[:100].strip(),
        "long_desc": desc.strip(),
        "features": [],
        "attributes": attrs,
        "overall_confidence": 0.4 if attrs else 0.2,
    }


def _llm_extract(mfg_part_num: str, part_desc: str, part_manuf: str) -> dict:
    import anthropic  # imported lazily so heuristic mode has zero hard deps

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    user_msg = (
        f"Mfg_Part_Num: {mfg_part_num}\n"
        f"Part_Desc: {part_desc}\n"
        f"Part_Manuf (raw, may include internal supplier code in parens): {part_manuf}\n"
    )
    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1500,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def extract(mfg_part_num: str, part_desc: str, part_manuf: str) -> ExtractionResult:
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return ExtractionResult(raw=_llm_extract(mfg_part_num, part_desc, part_manuf), mode="llm")
        except Exception as e:  # fall back gracefully rather than crash the batch
            fallback = _heuristic_extract(mfg_part_num, part_desc, part_manuf)
            fallback["_llm_error"] = str(e)
            return ExtractionResult(raw=fallback, mode="heuristic_after_error")
    return ExtractionResult(raw=_heuristic_extract(mfg_part_num, part_desc, part_manuf), mode="heuristic")
