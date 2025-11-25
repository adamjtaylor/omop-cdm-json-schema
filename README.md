# OMOP CDM JSON Schema Converter

Convert OMOP Common Data Model 5.4 field-level metadata into JSON Schema draft-07 files with embedded vocabulary enums for UI validation and data entry applications.

## Features

- ✅ **Complete OMOP CDM 5.4 coverage** - All 39 tables converted to JSON Schema
- ✅ **Vocabulary enums** - 2.5M standard concepts from OMOP vocabularies
- ✅ **UI-ready dropdowns** - Human-readable labels (e.g., "8507 - MALE")
- ✅ **Self-contained schemas** - No external dependencies or runtime lookups
- ✅ **Standard compliant** - JSON Schema draft-07 with oneOf validation
- ✅ **Zero dependencies** - Pure Python standard library + Bash

## Quick Start

```bash
# Run the converter
./convert.sh

# Schemas will be generated in schemas/ directory
ls -lh schemas/*.json
```

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation & Setup](#installation--setup)
3. [Project Structure](#project-structure)
4. [Generated Schemas](#generated-schemas)
5. [Usage Examples](#usage-examples)
6. [Configuration](#configuration)
7. [Output Statistics](#output-statistics)
8. [Troubleshooting](#troubleshooting)
9. [Performance Notes](#performance-notes)
10. [Contributing](#contributing)
11. [References](#references)

## Prerequisites

Before running the converter, ensure you have:

- **Python 3.7+** - Standard library only, no packages to install
- **Bash shell** - macOS/Linux or WSL on Windows
- **OMOP Vocabularies** - CONCEPT.csv from Athena (see setup below)
- **Disk space** - ~1GB for vocabularies, ~800MB for generated schemas
- **RAM** - ~2GB available during conversion

## Installation & Setup

### Step 1: Get OMOP Vocabularies

The converter requires the CONCEPT.csv file from OMOP vocabularies:

1. Visit [Athena](https://athena.ohdsi.org/)
2. Create a free account if needed
3. Create a vocabulary bundle download:
   - Select all vocabularies (or at minimum: SNOMED, RxNorm, LOINC)
   - Include both standard and classification vocabularies
   - Download the bundle (~400MB compressed)
4. Extract the downloaded bundle
5. Locate the `CONCEPT.csv` file (~828MB)
6. Place it in `../test1/athena_export_YYYYMMDD/CONCEPT.csv`

**Note:** The script will automatically create a symlink from `data/CONCEPT.csv` to your vocabulary export location.

### Step 2: Verify Repository Structure

Your directory should look like this:

```
omop-cdm-playground/
├── test1/
│   └── athena_export_20251021/
│       └── CONCEPT.csv          # Downloaded from Athena
└── test2/                       # This directory
    ├── convert.sh
    ├── convert_to_schemas.py
    ├── README.md
    └── BACKGROUND.md
```

### Step 3: Run the Conversion

```bash
cd test2
chmod +x convert.sh
./convert.sh
```

**What happens during execution:**

1. **Directory setup** - Creates `data/` and `schemas/` directories
2. **CSV download** - Fetches OMOP CDM 5.4 field-level metadata from GitHub
3. **Vocabulary linking** - Symlinks your CONCEPT.csv file
4. **Concept loading** - Loads 6.3M concepts, filters to 2.5M standard concepts
5. **oneOf building** - Creates sorted oneOf constraints with human-readable titles
6. **Schema generation** - Writes 39 JSON Schema files with embedded oneOf constraints

**Expected output:**

```
=== OMOP CDM 5.4 to JSON Schema Converter ===

Creating directories...
CSV file already exists: data/OMOP_CDMv5.4_Field_Level.csv
CONCEPT.csv already exists: data/CONCEPT.csv

Converting CSV to JSON schemas...
Loading CSV from data/OMOP_CDMv5.4_Field_Level.csv...
Loaded 432 rows
Grouping by table...
Found 39 tables
Loading CONCEPT vocabulary from data/CONCEPT.csv...
  Loaded 500,000 concepts...
  Loaded 1,000,000 concepts...
  ...
  Loaded 6,328,777 total concepts
  Found 32 domains
Building oneOf mappings...
  INFO: Domain 'Drug' has 2,048,628 concepts
  INFO: Domain 'Condition' has 105,667 concepts
  ...
Built oneOf constraints for 32 domains

Generating schemas...
  ✓ person (18 fields)
  ✓ visit_occurrence (17 fields)
  ✓ drug_exposure (23 fields)
  ...

Success! Generated 39 schema files in schemas/
```

**Timing:** First run takes 10-30 seconds depending on system performance.

## Project Structure

```
test2/
├── convert.sh                      # Bash orchestration script
├── convert_to_schemas.py           # Python conversion logic (318 lines)
├── README.md                       # This file
├── BACKGROUND.md                   # Design decisions and technical details
├── data/
│   ├── OMOP_CDMv5.4_Field_Level.csv   # CDM field metadata (auto-downloaded)
│   └── CONCEPT.csv                     # Vocabulary file (symlink)
└── schemas/                        # Generated JSON Schema files (759MB)
    ├── person.schema.json          # 110KB - Person demographic data
    ├── visit_occurrence.schema.json# 9.9MB - Healthcare encounters
    ├── drug_exposure.schema.json   # 227MB - Drug administration events
    ├── condition_occurrence.schema.json # 8.7MB - Condition/diagnosis events
    ├── measurement.schema.json     # 9.6MB - Lab results and vitals
    └── ... (39 total)
```

## Generated Schemas

### What's Included

Each generated JSON Schema file contains:

- **JSON Schema draft-07 format** - Industry standard validation
- **Table-level metadata** - Title, description, primary keys, foreign keys
- **Field definitions** - Type, format, maxLength, descriptions
- **Required fields array** - Validates mandatory fields
- **oneOf constraints** - Valid concept IDs with titles for CONCEPT foreign keys
- **x-primaryKey array** - Primary key fields
- **x-foreignKeys array** - Foreign key relationships with domain info

### Example Schema Structure

**person.schema.json** (simplified excerpt):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Person",
  "type": "object",
  "properties": {
    "person_id": {
      "type": "integer",
      "description": "User Guidance: It is assumed that every person with a different unique identifier is in fact a different person...\n\nETL Conventions: Any person linkage that needs to occur to uniquely identify Persons ought to be done prior to writing this table..."
    },
    "gender_concept_id": {
      "type": "integer",
      "oneOf": [
        {"const": 0, "title": "0 - No matching concept"},
        {"const": 8507, "title": "8507 - MALE"},
        {"const": 8532, "title": "8532 - FEMALE"}
      ],
      "description": "User Guidance: This field is meant to capture the biological sex at birth of the Person...\n\nETL Conventions: Use the gender or sex value present in the data..."
    },
    "year_of_birth": {
      "type": "integer",
      "description": "User Guidance: Compute age using year_of_birth..."
    },
    "race_concept_id": {
      "type": "integer",
      "oneOf": [
        {"const": 0, "title": "0 - No matching concept"},
        {"const": 8515, "title": "8515 - Asian"},
        {"const": 8516, "title": "8516 - Black or African American"},
        ...1404 more
      ]
    }
  },
  "required": ["person_id", "gender_concept_id", "year_of_birth", "race_concept_id", "ethnicity_concept_id"],
  "x-primaryKey": ["person_id"],
  "x-foreignKeys": [
    {
      "field": "gender_concept_id",
      "table": "CONCEPT",
      "fieldInTable": "CONCEPT_ID",
      "domain": "Gender"
    },
    ...
  ]
}
```

### oneOf Format

All concept fields include a `oneOf` array with `const` and `title` properties:

- **`oneOf` array** - List of valid concept options
- **`const` property** - The exact concept ID value (integer)
- **`title` property** - Human-readable label in "ID - Name" format

**Example:**
```json
"gender_concept_id": {
  "type": "integer",
  "oneOf": [
    {"const": 0, "title": "0 - No matching concept"},
    {"const": 8507, "title": "8507 - MALE"},
    {"const": 8532, "title": "8532 - FEMALE"}
  ]
}
```

This format enables:
- **Validation** - JSON Schema validators reject invalid concept IDs
- **UI dropdowns** - Extract titles for select/dropdown elements
- **Database storage** - Store integer IDs (const values)
- **Human readability** - Display names via title property

## Usage Examples

### Example 1: Validate OMOP Data with Python

```python
import json
import jsonschema

# Load schema
with open('schemas/person.schema.json') as f:
    person_schema = json.load(f)

# Valid person record
valid_person = {
    "person_id": 12345,
    "gender_concept_id": 8507,      # Male
    "year_of_birth": 1990,
    "race_concept_id": 8527,        # White
    "ethnicity_concept_id": 38003564 # Not Hispanic
}

# Validate
try:
    jsonschema.validate(valid_person, person_schema)
    print("✓ Valid OMOP person record")
except jsonschema.ValidationError as e:
    print(f"✗ Validation error: {e.message}")

# Invalid record (wrong gender ID)
invalid_person = {
    "person_id": 12346,
    "gender_concept_id": 9999999,  # Invalid concept ID
    "year_of_birth": 1985
}

try:
    jsonschema.validate(invalid_person, person_schema)
except jsonschema.ValidationError as e:
    print(f"✗ Expected error: {e.message}")
    # Output: "9999999 is not one of [0, 8507, 8532]"
```

### Example 2: Generate UI Dropdown Options

```python
import json

# Load schema
with open('schemas/person.schema.json') as f:
    schema = json.load(f)

# Extract gender oneOf options
gender_field = schema['properties']['gender_concept_id']
options = gender_field['oneOf']

# Generate HTML select options
print("<select name='gender_concept_id'>")
for option in options:
    concept_id = option['const']
    label = option['title']
    print(f"  <option value='{concept_id}'>{label}</option>")
print("</select>")

# Output:
# <select name='gender_concept_id'>
#   <option value='0'>0 - No matching concept</option>
#   <option value='8507'>8507 - MALE</option>
#   <option value='8532'>8532 - FEMALE</option>
# </select>
```

### Example 3: Build Dynamic Form with React

```javascript
import personSchema from './schemas/person.schema.json';

function GenderSelect() {
  const genderField = personSchema.properties.gender_concept_id;

  return (
    <select name="gender_concept_id">
      {genderField.oneOf.map(option => (
        <option key={option.const} value={option.const}>
          {option.title}
        </option>
      ))}
    </select>
  );
}
```

### Example 4: Validate CSV Data Import

```python
import csv
import json
import jsonschema

# Load schema
with open('schemas/person.schema.json') as f:
    person_schema = json.load(f)

# Validate CSV rows
errors = []
with open('person_data.csv') as f:
    reader = csv.DictReader(f)
    for row_num, row in enumerate(reader, start=2):
        # Convert string values to integers
        person = {
            'person_id': int(row['person_id']),
            'gender_concept_id': int(row['gender_concept_id']),
            'year_of_birth': int(row['year_of_birth']),
            # ... other fields
        }

        try:
            jsonschema.validate(person, person_schema)
        except jsonschema.ValidationError as e:
            errors.append((row_num, e.message))

if errors:
    print(f"Found {len(errors)} validation errors:")
    for row, msg in errors[:10]:  # Show first 10
        print(f"  Row {row}: {msg}")
else:
    print("✓ All rows valid!")
```

## Configuration

### Bash Script Variables (convert.sh)

Edit `convert.sh` to customize paths:

```bash
# Path to OMOP CDM field metadata (auto-downloaded)
CSV_URL="https://raw.githubusercontent.com/OHDSI/CommonDataModel/refs/heads/main/inst/csv/OMOP_CDMv5.4_Field_Level.csv"

# Path to CONCEPT vocabulary file
CONCEPT_SOURCE="../test1/athena_export_20251021/CONCEPT.csv"

# Output directories
DATA_DIR="data"
SCHEMAS_DIR="schemas"
```

### Python Script Customization (convert_to_schemas.py)

Key functions you can modify:

**Filter concept selection:**
```python
def load_concept_data(concept_csv_path):
    # Current: Only standard_concept = 'S'
    if standard_concept != 'S' and concept_id != '0':
        continue

    # Custom: Add domain filtering
    # if domain_id not in ['Gender', 'Race', 'Visit']:
    #     continue
```

**Change title format:**
```python
def build_concept_enum_mapping(concept_data):
    # Current: "ID - Name"
    one_of_array.append({
        "const": concept_id,
        "title": f"{concept_id} - {concept_name}"
    })

    # Alternative: "Name (ID)"
    # one_of_array.append({
    #     "const": concept_id,
    #     "title": f"{concept_name} ({concept_id})"
    # })
```

**Limit oneOf sizes:**
```python
# Add size limit per domain
if len(sorted_ids) > 1000:
    print(f"  WARNING: Truncating {domain} to 1000 concepts")
    sorted_ids = sorted_ids[:1000]
```

## Output Statistics

**Generated files:**
- 39 JSON Schema files (one per OMOP CDM table)
- Total size: 759MB
- 39 fields with oneOf constraints

**Domain sizes:**

| Domain | Concepts | Example Fields |
|--------|----------|----------------|
| Gender | 3 | gender_concept_id |
| Ethnicity | 151 | ethnicity_concept_id |
| Race | 1,407 | race_concept_id |
| Visit | 264 | visit_concept_id |
| Type Concept | 81 | *_type_concept_id |
| Unit | 1,040 | unit_concept_id |
| Condition | 105,667 | condition_concept_id |
| Measurement | 94,799 | measurement_concept_id |
| Procedure | 58,159 | procedure_concept_id |
| Device | 32,169 | device_concept_id |
| **Drug** | **2,048,628** | drug_concept_id |

**Largest schema files:**

| Schema | Size | oneOf Fields |
|--------|------|--------------|
| drug_exposure.schema.json | 227MB | drug_concept_id (2M+ options) |
| drug_era.schema.json | 227MB | drug_concept_id (2M+ options) |
| dose_era.schema.json | 227MB | drug_concept_id (2M+ options) |
| measurement.schema.json | 9.6MB | measurement_concept_id (94K options) |
| condition_occurrence.schema.json | 8.7MB | condition_concept_id (105K options) |
| person.schema.json | 110KB | gender, race, ethnicity (small oneOf) |

## Troubleshooting

### Issue: CONCEPT.csv not found

**Error message:**
```
WARNING: CONCEPT.csv not found at ../test1/athena_export_20251021/CONCEPT.csv
Schemas will be generated without oneOf constraints
```

**Solution:**
1. Download vocabulary bundle from [Athena](https://athena.ohdsi.org/)
2. Extract CONCEPT.csv
3. Place in `../test1/athena_export_*/CONCEPT.csv`
4. Or update `CONCEPT_SOURCE` path in `convert.sh`

**Schemas without oneOf:**
Schemas will still be generated, but concept fields won't have oneOf constraints. They'll be plain integers without validation constraints.

### Issue: Out of memory

**Error message:**
```
MemoryError: Unable to allocate array
```

**Solution:**
The converter requires ~2GB RAM during concept loading. Try:
- Close other applications
- Increase Docker memory limit (if using Docker)
- Use a machine with more RAM
- Modify script to limit domains (see Configuration)

### Issue: Schemas too large to load

**Symptom:**
Application crashes or hangs when loading drug_exposure.schema.json (227MB)

**Explanation:**
This is expected behavior. The Drug domain has 2M+ concepts, resulting in large files.

**Solutions:**
- **Lazy loading:** Don't load entire schema at once
- **Streaming:** Parse JSON in chunks
- **Pagination:** Load enum values on-demand
- **Caching:** Cache parsed schemas
- **Filtering:** Generate schemas with limited domains (see Configuration)

**Example lazy loading:**
```python
import json
import mmap

# Memory-map large file
with open('schemas/drug_exposure.schema.json', 'r') as f:
    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
        # Parse specific sections only
        schema = json.loads(m)
        required_fields = schema['required']  # Small section
        # Don't access properties with oneOf unless needed
```

### Issue: Missing oneOf for some CONCEPT foreign keys

**Symptom:**
Fields like `observation_concept_id` or `drug_source_concept_id` don't have oneOf constraints.

**Explanation:**
oneOf constraints are only added when:
1. Field is a foreign key to CONCEPT table
2. FK metadata includes a domain specification
3. Domain exists in CONCEPT vocabulary

Many CONCEPT foreign keys in the CDM metadata lack domain specifications, so they don't get oneOf constraints.

**Check foreign key metadata:**
```python
import json
with open('schemas/observation.schema.json') as f:
    schema = json.load(f)

for fk in schema['x-foreignKeys']:
    print(f"{fk['field']}: domain = {fk.get('domain', 'NO DOMAIN')}")
```

**Example output:**
```
observation_type_concept_id: domain = Type Concept
unit_concept_id: domain = Unit
observation_concept_id: domain = NO DOMAIN
observation_source_concept_id: domain = NO DOMAIN
```

Fields without domains won't have oneOf constraints because we don't know which concepts are valid.

### Issue: Conversion takes too long

**Symptom:**
Script runs for several minutes with no output.

**Explanation:**
Loading 6.3M concepts takes time. Progress is logged every 500K rows.

**Normal timing:**
- Load CONCEPT.csv: 5-10 seconds
- Build oneOf mappings: 2-5 seconds
- Generate schemas: 10-20 seconds
- **Total: 10-30 seconds**

**If longer than 2 minutes:**
- Check if CONCEPT.csv is corrupt
- Ensure sufficient RAM (may swap to disk)
- Check disk I/O performance

## Performance Notes

**Conversion performance:**
- **Initial run:** 10-30 seconds (varies by system)
- **Re-runs:** Same time (no caching implemented)
- **Memory usage:** 2GB peak during oneOf building
- **Disk I/O:** Tab-separated parsing optimized with csv.DictReader

**Schema file sizes:**
- **Small domains:** <1MB (Gender, Race, Visit)
- **Medium domains:** 1-10MB (Condition, Measurement)
- **Large domains:** 100-300MB (Drug)
- **Total:** 759MB

**Application performance tips:**
1. **Don't load all schemas** - Load only tables you need
2. **Lazy load oneOf** - Load oneOf arrays on-demand
3. **Cache parsed schemas** - Parse once, reuse
4. **Index by ID** - Convert oneOf arrays to hashmaps
5. **Compress** - Gzip schemas for distribution (~20MB per drug schema)

**Example caching:**
```python
import json
from functools import lru_cache

@lru_cache(maxsize=50)
def load_schema(table_name):
    with open(f'schemas/{table_name}.schema.json') as f:
        return json.load(f)

# First call: loads from disk
person_schema = load_schema('person')

# Subsequent calls: returns cached version
person_schema_again = load_schema('person')
```

## Contributing

### Reporting Issues

Found a bug or have a suggestion? Please report it:

1. Check existing issues on GitHub
2. Create new issue with:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - System info (Python version, OS)
   - Error messages/logs

### Extending the Converter

**Add support for new OMOP CDM versions:**

1. Update `CSV_URL` in `convert.sh` to point to new CDM version
2. Test conversion with new field metadata
3. Check for schema compatibility changes

**Add custom vocabulary tables:**

1. Download additional vocabulary CSV files (DOMAIN, VOCABULARY, etc.)
2. Modify `load_concept_data()` to load new files
3. Update `build_table_schema()` to reference new vocabularies

**Add compression:**

```python
import gzip
import json

def write_schema_file(table_name, schema, output_dir):
    filename = f"{table_name}.schema.json.gz"
    filepath = os.path.join(output_dir, filename)

    with gzip.open(filepath, 'wt', encoding='utf-8') as f:
        json.dump(schema, f, indent=2)
```

## References

### OMOP CDM Resources

- **OHDSI CommonDataModel** - https://github.com/OHDSI/CommonDataModel
- **CDM v5.4 Documentation** - https://ohdsi.github.io/CommonDataModel/cdm54.html
- **Athena Vocabulary** - https://athena.ohdsi.org/
- **OMOP Forums** - https://forums.ohdsi.org/

### JSON Schema Resources

- **JSON Schema Specification** - https://json-schema.org/draft-07/schema
- **Understanding JSON Schema** - https://json-schema.org/understanding-json-schema/
- **JSON Schema Validation** - https://json-schema.org/draft-07/json-schema-validation.html

### Python Libraries

- **jsonschema** - https://python-jsonschema.readthedocs.io/ (for validation)
- **csv** - https://docs.python.org/3/library/csv.html (stdlib, used in converter)
- **json** - https://docs.python.org/3/library/json.html (stdlib, used in converter)

### Related Projects

- **OMOP CDM Schema Builder** - This project
- **OHDSI WebAPI** - REST API for OMOP CDM
- **ATLAS** - OHDSI analytics platform

---

## License

This project is provided as-is for use with OMOP Common Data Model implementations. The OMOP CDM itself is maintained by OHDSI and follows their licensing terms.

## Acknowledgments

- **OHDSI Community** - For developing and maintaining OMOP CDM
- **Athena Team** - For providing standardized vocabularies
- **Contributors** - Everyone who has provided feedback and improvements

---

**For detailed design decisions and technical implementation details, see [BACKGROUND.md](BACKGROUND.md)**
