"""
schema.py
---------
Defines the exact 252-column "Delivery Format" header the output CSV must match,
built programmatically so it can never drift from the spec (50 dynamic
ATTRIBUTE_LABEL/VALUE/UOM triplets, 20 ITEM_FEATURES slots, etc).

If the delivery format ever changes, regenerate this from the real header:
    python -c "from pipeline.schema import dump_header_from_csv; dump_header_from_csv('data/Unihack__Expected_Output_-_Delivery_Format.csv')"
"""

N_ATTRIBUTES = 50
N_FEATURES = 20

STATIC_HEADER_BLOCK_1 = [
    "MFR URL", "Ref URL 1", "Ref URL 2", "Ref URL 3", "Ref URL 4", "Ref URL 5",
    "PART_NUMBER", "Dept", "Class", "Fine", "SKU - MY_PART_NUMBER",
    "Mfg_Part_Num", "Part_Desc", "E1_Brand", "Unilog_Brand", "DIB_Brand",
    "Part_Manuf", "MANUFACTURER_NAME", "BRAND_NAME", "TRADE_NAME",
    "MANUFACTURER_PART_NUMBER", "ALTERNATE_PART_NUMBER", "Classpath",
    "MOBILE_DESC", "INVOICE_DESC", "SHORT_DESC", "LONG_DESC1", "RETAIL_DESC",
    "MARKETING_DESCRIPTION",
]

FEATURE_COLS = [f"ITEM_FEATURES_{i}" for i in range(1, N_FEATURES + 1)]

STATIC_HEADER_BLOCK_2 = [
    "With", "Standard/Approvals", "Prop 65", "Application", "Includes",
    "Product Name",
]


def attribute_cols():
    cols = []
    for i in range(1, N_ATTRIBUTES + 1):
        cols += [f"ATTRIBUTE_LABEL {i}", f"ATTRIBUTE_VALUE {i}", f"ATTRIBUTE_UOM {i}"]
    return cols


STATIC_HEADER_BLOCK_3 = [
    "UPC", "EAN", "GTIN", "UNSPSC", "Warranty", "List Price", "Selling Qty",
    "Selling UOM", "Standard Packaging Information",
    "LENGTH", "LENGTH_UOM", "HEIGHT", "HEIGHT_UOM", "WIDTH", "WIDTH_UOM",
    "WEIGHT", "WEIGHT_UOM", "VOLUME", "VOLUME_UOM",
    "Product Image", "Alternate Image 1", "Alternate Image 2",
    "Alternate Image 3", "Alternate Image 4",
    "SDS", "SDS_1", "Warranty Information", "Catalog", "Specification Sheet",
    "Instruction/Installation Manual", "Service Manual", "Owners/User Manual",
    "Line Drawing", "MTR", "RoHS", "Full Engineering Drawing",
    "Energy Star Guide", "Technical Bulletin", "Submittal",
    "Compatibility Chart", "Size Chart", "Product Label/Insert",
    "Video Link", "Video Link 1", "Country Of Origin", "Discontinued",
    "Actual Image (Yes/No)",
]

OUTPUT_HEADER = (
    STATIC_HEADER_BLOCK_1
    + FEATURE_COLS
    + STATIC_HEADER_BLOCK_2
    + attribute_cols()
    + STATIC_HEADER_BLOCK_3
)

INPUT_COLUMNS = [
    "Mfg_Part_Num", "Part_Desc", "E1_Brand", "Unilog_Brand", "DIB_Brand", "Part_Manuf",
]


def empty_output_row() -> dict:
    return {c: "" for c in OUTPUT_HEADER}


def dump_header_from_csv(path: str):
    """Utility: print the real header as a Python list, to diff against OUTPUT_HEADER."""
    import csv
    with open(path, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    print(header)
    return header


if __name__ == "__main__":
    assert len(OUTPUT_HEADER) == 252, f"expected 252 cols, got {len(OUTPUT_HEADER)}"
    print(f"OUTPUT_HEADER OK — {len(OUTPUT_HEADER)} columns")
