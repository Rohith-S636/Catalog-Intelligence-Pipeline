# Catalog Intelligence Pipeline

Turns sparse product input rows — just a manufacturer part number, a terse
internal description, and a supplier name — into fully structured, 252-column
PIM-ready catalog records, with a confidence/provenance trail for every field.

This matches the actual Unihack dataset shape:

**Input** (`Mfg_Part_Num, Part_Desc, E1_Brand, Unilog_Brand, DIB_Brand, Part_Manuf`):
```
DCB518ASTS06G,"DCB518ASTS06G Diablo 1/2""x18"" - Sanding Belt 6pc",-- Unbranded --,-- No Unilog Brand --,-- No DIB Brand --,Freud Inc (2435)
```

**Output**: the full 252-column delivery format — classification (Dept/Class/Fine),
manufacturer/brand fields, multiple description variants, up to 20 feature
bullets, up to 50 structured `ATTRIBUTE_LABEL/VALUE/UOM` triplets, plus a
sidecar CSV logging **confidence + source** for every single field written.

## Why this is the actual hard part

Most of the 252 columns (images, SDS, warranty docs, dimensions) simply have
no signal in the input at all — that's honest and expected; they're left
blank rather than fabricated. The real extraction problem is squeezing every
usable signal out of a one-line description: pack sizes, grit codes,
dimensions, product line, category — and being explicit about confidence
instead of quietly guessing.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Offline / no API key — runs the rule-based fallback extractor
python -m pipeline.build_output \
  --input data/Unihack__Sample_Dataset_-_Input.csv \
  --output out/delivery.csv \
  --confidence-out out/confidence.csv \
  --limit 20

# With an Anthropic API key — runs the real LLM extraction agent
cp .env.example .env   # add ANTHROPIC_API_KEY=sk-...
export $(cat .env | xargs)
python -m pipeline.build_output \
  --input data/Unihack__Sample_Dataset_-_Input.csv \
  --output out/delivery.csv \
  --confidence-out out/confidence.csv \
  --limit 20
```

Drop `--limit` to run the full 1,000-row sample file.

## How it works

| File | Role |
|---|---|
| `pipeline/schema.py` | Programmatically builds the exact 252-column header (50 attribute triplets, 20 feature slots) so output can never drift from spec. Includes a diff utility against the real delivery-format CSV. |
| `pipeline/extractor.py` | The extraction agent. LLM mode (Claude) classifies category, cleans manufacturer/brand, writes description variants, and extracts up to 15 structured attributes — each with its own confidence + source string. Falls back to a conservative regex/keyword extractor if no API key is set, so the pipeline is runnable offline. |
| `pipeline/build_output.py` | Orchestrator: reads input CSV → runs extraction per row → maps results onto the 252-column schema → writes delivery CSV + a per-field confidence/provenance sidecar CSV. Flags any row with `overall_confidence < 0.5` for human review. |

### Confidence sidecar (`out/confidence.csv`)

One row per **field**, not per SKU — this is what a review UI reads to
color-code fields and show "why did the model write this":

```
Mfg_Part_Num,field,value,confidence,source,extraction_mode
DCB518ASTS06G,ATTRIBUTE_VALUE 1,"1/2"" x 18""",0.9,"Part_Desc literal (regex size match)",heuristic
```

Passthrough input fields (things literally given, not inferred) are always
logged at confidence `1.0` with source `"input file, verbatim"` — the sidecar
distinguishes *given* data from *inferred* data, which is the whole point of
the traceability requirement.

## Known limitations (honest, not hidden)

- The offline heuristic extractor is a rough fallback, not the real system —
  e.g. its size regex can mis-split fractional dimensions like `1/2"x18"`.
  It exists so the pipeline is demoable without an API key; the LLM mode is
  the intended path.
- No web/manufacturer-datasheet retrieval step yet (planned — see below).
- Category classification is currently a flat 3-level guess; no ETIM/UNSPSC
  taxonomy mapping is wired in yet.

## Roadmap (next, if more build time)

1. **Manufacturer datasheet retrieval** — when `Part_Manuf` + `Mfg_Part_Num`
   are known but the description is too sparse, fetch the manufacturer's
   public datasheet/spec page before extracting (the "limited inputs"
   retrieval step from the original design).
2. **ETIM/UNSPSC taxonomy mapping** — map `Dept/Class/Fine` to real industrial
   taxonomy codes instead of a free-text guess (`UNSPSC` column already
   exists in the schema, currently unfilled).
3. **Knowledge graph + review UI** — Neo4j graph (Product / Attribute /
   Source / Manufacturer nodes) and a React review dashboard reading
   `out/confidence.csv`, so low-confidence fields route to a human queue
   instead of auto-publishing.
4. **Manufacturer-template caching** — once one datasheet from a supplier is
   parsed, cache its layout so the next SKU from the same supplier is
   near-instant.

## Project structure

```
catalog-intel/
├── pipeline/
│   ├── schema.py         # 252-column header definition
│   ├── extractor.py      # extraction agent (LLM + heuristic fallback)
│   └── build_output.py   # orchestrator: CSV in -> CSV out + confidence log
├── data/
│   ├── Unihack__Sample_Dataset_-_Input.csv
│   └── Unihack__Expected_Output_-_Delivery_Format.csv
├── out/                  # generated output (gitignored)
├── requirements.txt
├── .env.example
└── README.md
```

## License

MIT (or update to match your hackathon's rules)
