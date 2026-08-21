"""
build_output.py
----------------
End-to-end: input CSV (6 sparse columns) -> output CSV (252-column delivery format)
+ a provenance/confidence sidecar CSV for the review UI.

Usage:
    python -m pipeline.build_output \
        --input data/Unihack__Sample_Dataset_-_Input.csv \
        --output out/delivery.csv \
        --confidence-out out/confidence.csv \
        --limit 20
"""

from __future__ import annotations
import argparse
import csv
import os
from tqdm import tqdm

from pipeline.schema import OUTPUT_HEADER, empty_output_row, INPUT_COLUMNS
from pipeline.extractor import extract, _clean_manufacturer

CONFIDENCE_HEADER = ["Mfg_Part_Num", "field", "value", "confidence", "source", "extraction_mode"]


def map_to_output_row(input_row: dict, extraction: dict, mode: str) -> tuple[dict, list[dict]]:
    row = empty_output_row()
    confidence_rows: list[dict] = []

    def set_field(col: str, value, confidence: float, source: str):
        row[col] = value if value is not None else ""
        confidence_rows.append({
            "Mfg_Part_Num": input_row.get("Mfg_Part_Num", ""),
            "field": col, "value": row[col],
            "confidence": round(confidence, 2), "source": source,
            "extraction_mode": mode,
        })

    # --- passthrough of raw input, verbatim, confidence 1.0 (it's given, not inferred) ---
    for col in INPUT_COLUMNS:
        set_field(col, input_row.get(col, ""), 1.0, "input file, verbatim")

    set_field("PART_NUMBER", input_row.get("Mfg_Part_Num", ""), 1.0, "input file, verbatim")
    set_field("MANUFACTURER_PART_NUMBER", input_row.get("Mfg_Part_Num", ""), 1.0, "input file, verbatim")

    # --- extracted / inferred fields ---
    overall_conf = extraction.get("overall_confidence", 0.3)

    set_field("MANUFACTURER_NAME", extraction.get("manufacturer_name", ""), overall_conf,
               "extraction agent: cleaned from Part_Manuf + description")
    set_field("BRAND_NAME", extraction.get("brand_name", ""), overall_conf,
               "extraction agent")
    set_field("Dept", extraction.get("dept", ""), overall_conf, "extraction agent: category classification")
    set_field("Class", extraction.get("class", ""), overall_conf, "extraction agent: category classification")
    set_field("Fine", extraction.get("fine", ""), overall_conf, "extraction agent: category classification")
    set_field("Classpath", extraction.get("classpath", ""), overall_conf, "extraction agent")
    set_field("Product Name", extraction.get("product_name", ""), overall_conf, "extraction agent")
    set_field("SHORT_DESC", extraction.get("short_desc", ""), overall_conf, "extraction agent")
    set_field("LONG_DESC1", extraction.get("long_desc", ""), overall_conf, "extraction agent")
    set_field("MOBILE_DESC", extraction.get("short_desc", ""), overall_conf, "derived from short_desc")
    set_field("INVOICE_DESC", input_row.get("Part_Desc", ""), 1.0, "input file, verbatim")

    # features -> ITEM_FEATURES_1..20
    for i, feat in enumerate(extraction.get("features", [])[:20], start=1):
        set_field(f"ITEM_FEATURES_{i}", feat, overall_conf, "extraction agent: feature parsing")

    # attributes -> ATTRIBUTE_LABEL/VALUE/UOM 1..50
    for i, attr in enumerate(extraction.get("attributes", [])[:50], start=1):
        set_field(f"ATTRIBUTE_LABEL {i}", attr.get("label", ""),
                   attr.get("confidence", overall_conf), attr.get("source", "extraction agent"))
        set_field(f"ATTRIBUTE_VALUE {i}", attr.get("value", ""),
                   attr.get("confidence", overall_conf), attr.get("source", "extraction agent"))
        set_field(f"ATTRIBUTE_UOM {i}", attr.get("uom", ""),
                   attr.get("confidence", overall_conf), attr.get("source", "extraction agent"))

    return row, confidence_rows


def run(input_path: str, output_path: str, confidence_path: str, limit: int | None):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(confidence_path) or ".", exist_ok=True)

    with open(input_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if limit:
        rows = rows[:limit]

    with open(output_path, "w", newline="", encoding="utf-8") as out_f, \
         open(confidence_path, "w", newline="", encoding="utf-8") as conf_f:

        out_writer = csv.DictWriter(out_f, fieldnames=OUTPUT_HEADER)
        out_writer.writeheader()
        conf_writer = csv.DictWriter(conf_f, fieldnames=CONFIDENCE_HEADER)
        conf_writer.writeheader()

        low_conf_count = 0
        for input_row in tqdm(rows, desc="Extracting"):
            result = extract(
                mfg_part_num=input_row.get("Mfg_Part_Num", ""),
                part_desc=input_row.get("Part_Desc", ""),
                part_manuf=input_row.get("Part_Manuf", ""),
            )
            out_row, conf_rows = map_to_output_row(input_row, result.raw, result.mode)
            out_writer.writerow(out_row)
            conf_writer.writerows(conf_rows)
            if result.raw.get("overall_confidence", 1.0) < 0.5:
                low_conf_count += 1

    print(f"Wrote {len(rows)} rows -> {output_path}")
    print(f"Provenance/confidence log -> {confidence_path}")
    print(f"{low_conf_count}/{len(rows)} rows flagged overall_confidence < 0.5 (route to human review)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default="out/delivery.csv")
    ap.add_argument("--confidence-out", default="out/confidence.csv")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    run(args.input, args.output, args.confidence_out, args.limit)


if __name__ == "__main__":
    main()
