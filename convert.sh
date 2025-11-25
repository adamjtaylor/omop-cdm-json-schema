#!/bin/bash

# OMOP CDM 5.4 to JSON Schema Converter
# Downloads CSV and converts to individual JSON Schema files

set -e

CSV_URL="https://raw.githubusercontent.com/OHDSI/CommonDataModel/refs/heads/main/inst/csv/OMOP_CDMv5.4_Field_Level.csv"
DATA_DIR="data"
SCHEMAS_DIR="schemas"
CSV_FILE="$DATA_DIR/OMOP_CDMv5.4_Field_Level.csv"
CONCEPT_FILE="$DATA_DIR/CONCEPT.csv"
CONCEPT_SOURCE="../test1/athena_export_20251021/CONCEPT.csv"

echo "=== OMOP CDM 5.4 to JSON Schema Converter ==="
echo

# Create directories
echo "Creating directories..."
mkdir -p "$DATA_DIR"
mkdir -p "$SCHEMAS_DIR"

# Download CSV if not present
if [ -f "$CSV_FILE" ]; then
    echo "CSV file already exists: $CSV_FILE"
else
    echo "Downloading CSV from GitHub..."
    curl -L -o "$CSV_FILE" "$CSV_URL"
    echo "Downloaded: $CSV_FILE"
fi

# Check for CONCEPT.csv and create symlink if needed
if [ ! -f "$CONCEPT_FILE" ]; then
    if [ -f "$CONCEPT_SOURCE" ]; then
        echo "Creating symlink to CONCEPT.csv..."
        ln -sf "$(cd "$(dirname "$CONCEPT_SOURCE")" && pwd)/$(basename "$CONCEPT_SOURCE")" "$CONCEPT_FILE"
        echo "Linked: $CONCEPT_FILE -> $CONCEPT_SOURCE"
    else
        echo "WARNING: CONCEPT.csv not found at $CONCEPT_SOURCE"
        echo "Schemas will be generated without enum values"
    fi
else
    echo "CONCEPT.csv already exists: $CONCEPT_FILE"
fi

echo

# Run Python conversion
echo "Converting CSV to JSON schemas..."
python3 convert_to_schemas.py

echo
echo "=== Conversion Complete ==="
echo "Schemas generated in: $SCHEMAS_DIR/"
echo "Schema count: $(ls -1 $SCHEMAS_DIR/*.json 2>/dev/null | wc -l | tr -d ' ')"
