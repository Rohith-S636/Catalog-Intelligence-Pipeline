# Catalog-Intelligence-Pipeline
AI pipeline that turns messy product datasheets, nameplates, and part numbers into structured, traceable catalog data — extraction agents + knowledge graph + confidence-scored review UI.
Turn messy, unstructured product data — PDF datasheets, nameplate photos, bare part numbers — into clean, structured, **traceable** catalog entries ready for commerce systems.

Built for industrial/electronic component catalogs, where a wrong voltage rating or missing certification isn't a cosmetic bug — it's a liability. Every extracted fact carries a pointer back to the exact source (page, table cell, or image region) and a confidence score, so humans review the 5–10% that need it instead of every field on every SKU.

## The problem

Distributors like Grainger and RS Group manage catalogs of hundreds of thousands to millions of SKUs, sourced from thousands of suppliers, each shipping data in a different format (PDF spec sheets, scanned nameplates, inconsistent part numbers). Keeping that data accurate and current is a large, ongoing, manual cost center — not a one-time cleanup job.

## What this does

1. **Extraction agents** — category-schema-guided extraction from text/tables (layout-aware parsing) and images (vision-language model) for nameplates, exploded diagrams, and dimension drawings. If only a part number is given, an agent retrieves the manufacturer datasheet first.
2. **Normalize & validate** — standardizes units, merges synonymous attribute names, maps to real industrial taxonomies (ETIM/UNSPSC), and flags cross-source conflicts instead of silently averaging them.
3. **Knowledge graph** — Product, Attribute, Value, Source Document, Manufacturer, Category, and Certification nodes, with every edge carrying full provenance (document, location, agent run, confidence).
4. **Review + commerce output** — high-confidence fields auto-publish; low-confidence or conflicting fields route to a lightweight human review queue with source snippets shown inline. Outputs structured, commerce-ready product records.

## Tech stack

| Layer | Tech |
|---|---|
| Backend / orchestration | Python, FastAPI |
| Document parsing | PyMuPDF / pdfplumber (text & tables), LLM vision model (images) |
| RAG / enrichment store | Chroma or FAISS |
| Knowledge graph | Neo4j Community Edition |
| Frontend | React + Tailwind |
| Storage | Postgres (or SQLite for local dev) |

LLM/vision calls are abstracted behind a thin provider interface so the model backend (Claude, GPT-4o, Gemini) is a config swap, not a rewrite.


