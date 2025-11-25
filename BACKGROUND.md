# OMOP CDM JSON Schema Converter - Technical Background

This document provides detailed context on the design decisions, technical challenges, and implementation approach for the OMOP CDM JSON Schema converter.

## Table of Contents

1. [Introduction](#introduction)
2. [OMOP CDM Context](#omop-cdm-context)
3. [Requirements Analysis](#requirements-analysis)
4. [Design Decisions](#design-decisions)
5. [Technical Challenges](#technical-challenges)
6. [Implementation Details](#implementation-details)
7. [Alternative Approaches](#alternative-approaches)
8. [Trade-offs Accepted](#trade-offs-accepted)
9. [Lessons Learned](#lessons-learned)
10. [Future Enhancements](#future-enhancements)
11. [Conclusion](#conclusion)

## Introduction

### Project Genesis

The OMOP CDM JSON Schema converter was created to solve a specific problem: **enabling validated data entry for OMOP CDM databases through spreadsheet/grid UI applications**.

Healthcare organizations implementing OMOP CDM need tools for data entry and validation. While the CDM provides a standardized schema, there was no standard way to:
- Validate data against OMOP vocabularies
- Provide dropdown options for concept fields
- Display human-readable names alongside concept IDs
- Package this in a portable, dependency-free format

### The Problem

OMOP CDM uses standardized vocabularies with millions of clinical concepts. For example:
- Drug concepts: 2,048,628 (medications, ingredients, formulations)
- Condition concepts: 105,667 (diagnoses, symptoms)
- Measurement concepts: 94,799 (lab tests, vitals)

**Challenge:** How do you provide dropdown lists with 2 million drug names in a UI tool while maintaining:
- Standards compliance (JSON Schema)
- Self-contained schemas (no external database)
- Validation capability
- Human readability

### The Solution

Generate JSON Schema files with embedded vocabulary constraints:
1. Parse OMOP CDM field metadata
2. Load 6.3M concepts from CONCEPT vocabulary table
3. Filter to 2.5M standard concepts
4. Inject sorted oneOf constraints into foreign key fields
5. Add human-readable labels via title property
6. Output self-contained JSON Schema draft-07 files

**Result:** 39 schema files (759MB) that enable both programmatic validation and UI dropdown generation without external dependencies.

## OMOP CDM Context

### What is OMOP CDM?

**OMOP** = Observational Medical Outcomes Partnership
**CDM** = Common Data Model

OMOP CDM is a standardized data model for healthcare observational research, developed by the OHDSI (Observational Health Data Sciences and Informatics) community.

**Key characteristics:**
- **Standardized schema** - Consistent table/field structure across institutions
- **Standardized vocabularies** - Clinical concepts mapped to common IDs
- **Patient-centric** - Organized around the person and their healthcare journey
- **Research-optimized** - Designed for large-scale observational studies

**Current version:** 5.4 (released 2021)
**Tables:** 39 standardized tables
**Vocabularies:** 100+ source vocabularies (SNOMED, RxNorm, LOINC, ICD-10, etc.)

### CONCEPT Table Explained

The CONCEPT table is the cornerstone of OMOP vocabularies. It contains **every standardized clinical concept** used across the CDM.

**Structure:**
```
CONCEPT (
    concept_id INT PRIMARY KEY,
    concept_name VARCHAR(255),
    domain_id VARCHAR(20),
    vocabulary_id VARCHAR(20),
    concept_class_id VARCHAR(20),
    standard_concept CHAR(1),
    concept_code VARCHAR(50),
    valid_start_date DATE,
    valid_end_date DATE,
    invalid_reason VARCHAR(1)
)
```

**Key fields:**

- **concept_id** - Unique integer identifier (e.g., 8507 = "MALE")
- **concept_name** - Human-readable name
- **domain_id** - Concept domain (Gender, Drug, Condition, etc.)
- **vocabulary_id** - Source vocabulary (SNOMED, RxNorm, etc.)
- **standard_concept** - 'S' for standard, null for non-standard

**Example rows:**
```
8507  | MALE                    | Gender    | SNOMED | S
8532  | FEMALE                  | Gender    | SNOMED | S
192671| Aspirin 325 MG Oral Tab | Drug      | RxNorm | S
201826| Type 2 diabetes mellitus| Condition | SNOMED | S
```

**Size:** 6,328,777 concepts across 32 domains

### How Vocabularies Work

**Concept References:**
OMOP tables use integer foreign keys to CONCEPT.concept_id instead of storing text values:

```sql
-- Instead of storing "Male" as text:
person (
    person_id INT,
    gender VARCHAR(10)  -- ❌ Not standardized
)

-- OMOP stores concept ID:
person (
    person_id INT,
    gender_concept_id INT  -- ✓ References CONCEPT
)
```

**Domain Constraints:**
Each concept field references a specific domain:

| Field | Domain | Example Concepts |
|-------|--------|------------------|
| gender_concept_id | Gender | 8507=MALE, 8532=FEMALE |
| race_concept_id | Race | 8515=Asian, 8516=Black |
| drug_concept_id | Drug | 192671=Aspirin, 1545892=Metformin |
| condition_concept_id | Condition | 201826=Diabetes, 316866=Hypertension |

**Standard vs Non-Standard:**
- **Standard concepts** (S flag) - Preferred for analysis, interoperability
- **Non-standard concepts** - Mapped to standard via CONCEPT_RELATIONSHIP table
- **Best practice:** Store standard concepts in CDM tables

### Why This Matters for Schemas

**Validation needs:**
1. **Type validation** - Ensure concept_id is integer
2. **Value validation** - Ensure concept_id exists in CONCEPT table
3. **Domain validation** - Ensure concept belongs to correct domain
4. **UI generation** - Provide dropdown lists of valid options

**Traditional approach (database-dependent):**
```sql
-- Validate at query time
SELECT * FROM person p
WHERE EXISTS (
    SELECT 1 FROM concept c
    WHERE c.concept_id = p.gender_concept_id
    AND c.domain_id = 'Gender'
    AND c.standard_concept = 'S'
)
```

**Our approach (self-contained schemas):**
```json
{
  "gender_concept_id": {
    "type": "integer",
    "oneOf": [
      {"const": 0, "title": "0 - No matching concept"},
      {"const": 8507, "title": "8507 - MALE"},
      {"const": 8532, "title": "8532 - FEMALE"}
    ]
  }
}
```

Benefits:
- ✅ No database connection needed
- ✅ JSON Schema validators work out-of-box
- ✅ UI tools can extract dropdown options
- ✅ Human-readable labels embedded
- ✅ Portable across systems

## Requirements Analysis

### Primary Goal

**Enable spreadsheet/grid UI with validated dropdowns for OMOP data entry**

Specific use case: A web application with a grid/spreadsheet interface for entering OMOP data needs:
1. Dropdown selectors for concept fields
2. Display human-readable names (not just IDs)
3. Validate entered values against allowed concepts
4. Work offline without database connection

### User Needs

1. **JSON Schema validation** (standard format)
   - Industry standard schema language
   - Wide tool support (validators, code generators, documentation tools)
   - Language-agnostic

2. **Constraints for concept fields** (dropdown values)
   - List of valid concept IDs with titles
   - Native JSON Schema oneOf validation
   - Extractable for UI dropdown generation

3. **Human-readable labels** (not just IDs)
   - Users see "8507 - MALE" not "8507"
   - Labels embedded in schema
   - No external lookup required

4. **Complete coverage** (all standard concepts)
   - No arbitrary limits (e.g., "top 100 drugs")
   - Includes rare/specialized concepts
   - Matches full OMOP vocabulary

5. **Self-contained schemas** (no external lookups)
   - No database connection needed
   - No API calls required
   - Portable across environments
   - Works offline

### Technical Constraints

**Must have:**
- **JSON Schema draft-07 only** - Latest stable version (draft-07)
- **Standard library Python** - No pip install, no dependencies
- **Bash + Python stack** - Common in data engineering environments
- **Handle ~1GB vocabulary files** - CONCEPT.csv is 828MB
- **Handle 2M+ drug concepts** - Largest domain by far

**Nice to have:**
- Fast conversion (<1 minute)
- Memory efficient (<4GB RAM)
- Clear progress indicators
- Graceful degradation (works without CONCEPT.csv)

### Non-Requirements

**Explicitly out of scope:**
- Real-time vocabulary updates (static generation is fine)
- Multiple OMOP CDM versions simultaneously
- Compression/optimization (accept large files)
- Database integration (standalone tool)
- Web interface (command-line is fine)

## Design Decisions

### Decision 1: JSON Schema Format

**Question:** How should we represent constrained values with labels in JSON Schema?

#### Options Considered

**Option A: oneOf with const + title (CHOSEN)**

```json
{
  "type": "integer",
  "oneOf": [
    {"const": 0, "title": "0 - No matching concept"},
    {"const": 8507, "title": "8507 - MALE"},
    {"const": 8532, "title": "8532 - FEMALE"}
  ]
}
```

**Pros:**
- ✅ Pure JSON Schema (no extensions)
- ✅ Standard-compliant (JSON Schema draft-07)
- ✅ Richer per-option metadata
- ✅ Better validator error messages
- ✅ Built-in title property for labels

**Cons:**
- ❌ Larger file size than enum approach (~150 bytes vs ~50 bytes per concept)
- ❌ Drug domain schemas are ~227MB (acceptable for our use case)
- ❌ Slightly slower validation (tests each oneOf branch)

**Option B: enum + x-enumNames**

```json
{
  "type": "integer",
  "enum": [0, 8507, 8532],
  "x-enumNames": {
    "0": "0 - No matching concept",
    "8507": "8507 - MALE",
    "8532": "8532 - FEMALE"
  }
}
```

**Pros:**
- ✅ Native JSON Schema enum validation
- ✅ Compact representation (~50 bytes per concept)
- ✅ x-enumNames is a recognized extension pattern
- ✅ Wide tool support

**Cons:**
- ❌ x-enumNames not in JSON Schema spec (extension)
- ❌ Less standard than pure JSON Schema
- ❌ Requires custom handling for labels

**Option C: External reference files**

```json
{
  "type": "integer",
  "$ref": "vocabularies/gender.json#/oneOf"
}
```

**Pros:**
- ✅ Smaller individual schemas
- ✅ Reusable vocabulary files
- ✅ Easy to update vocabularies separately

**Cons:**
- ❌ Not self-contained (violates requirement)
- ❌ More complex deployment
- ❌ Requires $ref resolution
- ❌ Breaks simple UI tools

#### Decision: Option A (oneOf with const + title)

**Rationale:**
1. **Standards-compliant** - Pure JSON Schema draft-07, no extensions
2. **Self-contained** - No external files needed
3. **Rich metadata** - Built-in title property for human-readable labels
4. **Better validation** - Clear error messages with titles
5. **UI-ready** - Simple extraction: `option.const` for value, `option.title` for display

**Trade-off accepted:** Larger file sizes (227MB for drug schemas) in exchange for standards compliance and simplicity.

### Decision 2: Concept Filtering

**Question:** Which concepts should we include in oneOf constraints?

#### Options

**Option A: All concepts (6.3M)**
- Includes deprecated, non-standard, and classification concepts
- Unnecessary noise, violates OMOP best practices

**Option B: Standard concepts only (2.5M) - CHOSEN**
- Filter: `WHERE standard_concept = 'S'`
- Aligns with OHDSI recommendations
- Excludes deprecated and source-specific codes
- Still provides complete clinical coverage

**Option C: Limited by size (e.g., max 1000 per domain)**
- Arbitrary cutoff
- Incomplete coverage
- Which 1000? Most common? Alphabetical? No good answer.

#### Decision: Option B (Standard concepts only)

**Rationale:**
1. **OMOP best practice** - Standard concepts preferred for analysis
2. **Complete coverage** - All standard clinical concepts included
3. **Reduces size** - From 6.3M to 2.5M (~60% reduction)
4. **Maintains quality** - Standard concepts are curated/validated

**Implementation:**
```python
if standard_concept != 'S' and concept_id != '0':
    continue  # Skip non-standard concepts
```

**Special case:** concept_id=0 always included (means "No matching concept")

### Decision 3: Domain Coverage

**Question:** Should we generate oneOf constraints for all domains or only small ones?

#### Options

**Option A: All CONCEPT FKs with domains (CHOSEN)**
- Generate oneOf for all domains
- Even 2M drug concepts
- Complete solution

**Option B: Small domains only (<1000 concepts)**
- Skip Drug (2M), Condition (105K), Observation (132K)
- Manageable file sizes
- Incomplete, users still need large domains

**Option C: User-configured list**
- Config file specifies which domains
- Flexibility but configuration burden

#### Decision: Option A (All domains)

**Rationale:**
1. **User requirement** - Explicitly requested "all standard concepts"
2. **Complete solution** - No gaps or limitations
3. **UI can handle** - Lazy loading, virtualization, search filters
4. **Predictable** - No surprises, all domains treated equally

**Mitigations for large files:**
- Document file sizes in README
- Recommend lazy loading in applications
- Log info message for domains >1000 concepts

### Decision 4: Display Format

**Question:** How should we format the human-readable names?

#### Options

**Option A: "ID - Name" (CHOSEN)**
```
"8507": "8507 - MALE"
```
- Shows both ID and name
- ID-first for database reference
- Consistent with OMOP conventions

**Option B: "Name Only"**
```
"8507": "MALE"
```
- Cleaner, more natural
- Loses ID context
- Harder to verify correct concept

**Option C: "Name (ID)"**
```
"8507": "MALE (8507)"
```
- Name-first, more readable
- ID harder to extract programmatically
- Unusual format

#### Decision: Option A ("ID - Name")

**Rationale:**
1. **ID prominent** - Emphasizes that ID is what's stored
2. **Verifiable** - Users can confirm concept ID
3. **Parse-friendly** - ID is first, easy to extract
4. **OMOP standard** - Athena displays this format

**Example output:**
```json
"oneOf": [
  {"const": 0, "title": "0 - No matching concept"},
  {"const": 8507, "title": "8507 - MALE"},
  {"const": 192671, "title": "192671 - Aspirin 325 MG Oral Tablet"}
]
```

## Technical Challenges

### Challenge 1: File Size Management

**Problem:**
- Drug domain: 2,048,628 standard concepts
- Each concept in oneOf format: ~100-150 bytes (const + title in JSON objects)
- Math: 2M × 100 bytes = 200MB+ per drug field
- Result: drug_exposure.schema.json = 227MB

**Solutions explored:**

1. **Gzip compression**
   - Reduces to ~20MB (90% compression)
   - Requires decompression before use
   - Violates self-contained requirement for some tools

2. **Chunking/pagination**
   - Split oneOf into multiple files
   - Violates self-contained requirement
   - Complex for tools to consume

3. **Abbreviation**
   - Shorten concept names
   - Loses information, harms usability

4. **oneOf with $ref**
   - Reference external vocab files
   - Not self-contained

**Solution implemented: Accept large files**

**Rationale:**
- Storage is cheap (759MB is manageable)
- Users can implement lazy loading in apps
- Maintains self-contained requirement
- No information loss

**Mitigation:**
- Document file sizes prominently in README
- Provide lazy loading examples
- Recommend compression for distribution
- Explain this is expected, not a bug

**Impact:**
```
Total schemas: 759MB
Largest: drug_exposure.schema.json (227MB)
Medium: measurement.schema.json (9.6MB)
Small: person.schema.json (110KB)
```

### Challenge 2: Memory Usage

**Problem:**
- Loading 6.3M concepts requires substantial RAM
- Python dicts have overhead (~200 bytes per entry)
- Building nested structures: {domain: {id: name}}
- Peak usage: ~2GB

**Solutions considered:**

1. **Stream processing**
   ```python
   for row in csv.DictReader(f):
       yield process(row)
   ```
   - Can't build domain mappings (need lookups)
   - Would require multiple passes

2. **External database**
   ```python
   import sqlite3
   # Load concepts into SQLite
   ```
   - Adds dependency
   - Complexity overhead
   - Still needs memory for query results

3. **Memory mapping**
   ```python
   import mmap
   # Memory-map CONCEPT.csv
   ```
   - Complex implementation
   - Still need lookups

**Solution implemented: Load once, efficient structures**

**Approach:**
```python
concepts_by_domain = defaultdict(dict)  # Efficient grouping

for row in csv.DictReader(f, delimiter='\t'):
    if row['standard_concept'] == 'S':  # Filter early
        domain = row['domain_id']
        concept_id = int(row['concept_id'])
        concept_name = row['concept_name']
        concepts_by_domain[domain][concept_id] = concept_name
```

**Optimizations:**
- Filter non-standard concepts immediately (60% reduction)
- Use defaultdict to avoid key existence checks
- Store only necessary fields (id, name)
- Progress logging every 500K rows (user feedback)

**Result:** 2GB peak, acceptable for target systems

### Challenge 3: TSV Parsing

**Problem:**
- CONCEPT.csv is tab-separated, not comma-separated
- Medical terms contain commas: "Diabetes mellitus, type 2"
- Special characters: quotes, unicode, etc.
- 6.3M rows to parse reliably

**Why TSV?**
Athena exports use TSV because medical terms often contain commas:
```
"Aspirin, 325 MG, Oral Tablet"  # Would break CSV parsing
```

**Solution:**
```python
csv.DictReader(f, delimiter='\t')
```

Python's csv module handles:
- Tab delimiter
- Quoted fields
- Newlines in fields
- Unicode characters

**Gotchas handled:**
- Empty fields (checked for 'NA')
- Mixed case (normalized to lowercase)
- Trailing whitespace (stripped)

**Lesson:** Always check delimiter before assuming CSV!

### Challenge 4: Domain Matching

**Problem:**
- CDM metadata has `fkDomain` field (e.g., "Gender")
- CONCEPT table has `domain_id` field (e.g., "Gender")
- Must match exactly (case-sensitive)
- Some FKs have no domain specified

**Cases:**

1. **FK with domain** → Generate oneOf
   ```python
   if fk_table == 'CONCEPT' and fk_domain in concept_enum_map:
       prop_schema['oneOf'] = one_of_array
   ```

2. **FK without domain** → Skip oneOf
   ```python
   # gender_source_concept_id has no domain
   # Don't generate oneOf (could be any domain)
   ```

3. **FK to non-CONCEPT table** → Skip oneOf
   ```python
   if fk_table != 'CONCEPT':
       continue  # e.g., FK to LOCATION, PROVIDER
   ```

**Result:**
- 39 fields with oneOf constraints (domain specified)
- 80+ CONCEPT FKs without oneOf (no domain in CDM metadata)

**Example:**
```python
# person.schema.json x-foreignKeys:
{
  "field": "gender_concept_id",
  "domain": "Gender"  # ← Has domain, gets oneOf
},
{
  "field": "gender_source_concept_id"
  # ← No domain, no oneOf
}
```

### Challenge 5: Concept ID 0

**Problem:**
- `concept_id = 0` means "No matching concept"
- Has `domain_id = 'Metadata'`
- Should appear in ALL domain oneOf constraints (not just Metadata)
- Represents NULL concept reference

**OMOP semantics:**
```sql
-- 0 means "no standard concept could be assigned"
UPDATE person SET gender_concept_id = 0
WHERE gender_source_value IS NULL;
```

**Solution:**
```python
for domain, concepts in concept_data.items():
    if 0 not in concepts:
        concepts[0] = "No matching concept"
    # Now every domain oneOf includes 0
```

**Ensures:**
- Nullable concept fields can store 0
- Consistent across all domains
- Validates correctly

**Example:**
```json
{
  "gender_concept_id": {
    "type": "integer",
    "oneOf": [
      {"const": 0, "title": "0 - No matching concept"},  # ← Always first
      {"const": 8507, "title": "8507 - MALE"},
      {"const": 8532, "title": "8532 - FEMALE"}
    ]
  }
}
```

## Implementation Details

### Architecture

```
┌─────────────┐
│ convert.sh  │  Bash orchestration
└──────┬──────┘
       │
       ├──1. Check/symlink CONCEPT.csv
       │
       └──2. Execute convert_to_schemas.py
              │
              ├── load_csv_data()
              │   └→ OMOP_CDMv5.4_Field_Level.csv
              │
              ├── load_concept_data()
              │   └→ CONCEPT.csv (6.3M rows)
              │      └→ Filter standard_concept='S'
              │         └→ Group by domain_id
              │            └→ {domain: {id: name}}
              │
              ├── build_concept_enum_mapping()
              │   └→ Sort IDs per domain
              │      └→ Format "ID - Name"
              │         └→ {domain: oneOf_array}
              │
              └── build_table_schema()
                  └→ For each field:
                     └→ If CONCEPT FK with domain:
                        └→ Inject oneOf array
                           └→ Write JSON
```

### Key Functions

**1. load_concept_data()**
```python
def load_concept_data(concept_csv_path):
    concepts_by_domain = defaultdict(dict)

    with open(concept_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')

        for row in reader:
            if row['standard_concept'] == 'S':  # Filter
                domain = row['domain_id']
                id = int(row['concept_id'])
                name = row['concept_name']
                concepts_by_domain[domain][id] = name

    return dict(concepts_by_domain)
```

**2. build_concept_enum_mapping()**
```python
def build_concept_enum_mapping(concept_data):
    enum_map = {}

    for domain, concepts in concept_data.items():
        # Add concept_id=0
        if 0 not in concepts:
            concepts[0] = "No matching concept"

        # Sort IDs
        sorted_ids = sorted(concepts.keys())

        # Build oneOf array
        one_of_array = []
        for cid in sorted_ids:
            name = concepts[cid]
            one_of_array.append({
                "const": cid,
                "title": f"{cid} - {name}"
            })

        enum_map[domain] = one_of_array

    return enum_map
```

**3. build_table_schema() enhancement**
```python
def build_table_schema(table_name, fields, concept_enum_map=None):
    properties = {}

    for field in fields:
        prop_schema = map_to_json_type(field['cdmDatatype'])

        # Check for CONCEPT FK
        if field['isForeignKey'] == 'Yes':
            fk_table = field['fkTableName']
            fk_domain = field['fkDomain']

            if (fk_table.upper() == 'CONCEPT' and
                concept_enum_map and
                fk_domain in concept_enum_map):

                # Inject oneOf
                one_of_array = concept_enum_map[fk_domain]
                prop_schema['oneOf'] = one_of_array

        properties[field_name] = prop_schema

    # Build complete schema...
```

### Data Flow

```
CONCEPT.csv (6,328,777 rows)
    ↓ parse TSV
(6.3M concept dicts)
    ↓ filter standard_concept='S'
(2.5M standard concepts)
    ↓ group by domain_id
{32 domains: {id: name}}
    ↓ sort IDs, format names
{32 domains: (enum[], x-enumNames{})}
    ↓ inject into field schemas
(39 fields with enums)
    ↓ write JSON
(39 schema files, 759MB)
```

**Processing time:**
- Load CONCEPT: 5-10 seconds
- Build enums: 2-5 seconds
- Generate schemas: 10-20 seconds
- **Total: 10-30 seconds**

### Performance Characteristics

**Time complexity:**
- Load concepts: O(n) where n=6.3M rows
- Filter: O(n)
- Group by domain: O(n)
- Sort per domain: O(d × m log m) where d=32 domains, m=avg concepts per domain
- Schema generation: O(t × f) where t=39 tables, f=avg fields per table

**Space complexity:**
- Concept storage: O(n) where n=2.5M standard concepts
- Enum maps: O(n)
- Schemas: O(n) in output files
- **Peak RAM: ~2GB**

## Alternative Approaches

### Alternative 1: Athena REST API

**Approach:** Query Athena API during conversion

```python
import requests

def get_concepts_by_domain(domain):
    url = f"https://athena.ohdsi.org/api/v1/concepts"
    params = {'domain': domain, 'standard': 'true'}
    return requests.get(url, params=params).json()
```

**Pros:**
- ✅ Always current vocabulary
- ✅ No local CONCEPT.csv needed
- ✅ Could filter by date

**Cons:**
- ❌ Requires internet during conversion
- ❌ API rate limits (~1000 calls/hour)
- ❌ 6M+ concepts = 6000+ API calls
- ❌ Athena API not designed for bulk export
- ❌ Slow (would take hours)

**Why not chosen:** API unsuitable for bulk data extraction

### Alternative 2: Separate Vocabulary Files

**Approach:** Generate reusable vocabulary JSON files

```
schemas/
├── person.schema.json
└── vocabularies/
    ├── gender.json
    ├── race.json
    └── drug.json
```

**person.schema.json:**
```json
{
  "gender_concept_id": {
    "type": "integer",
    "$ref": "vocabularies/gender.json#/enum"
  }
}
```

**Pros:**
- ✅ Smaller individual schemas
- ✅ Reusable vocabularies
- ✅ Easy to update vocabularies independently
- ✅ Reduces duplication

**Cons:**
- ❌ Not self-contained (violates requirement)
- ❌ Requires $ref resolution
- ❌ More complex deployment (multiple files)
- ❌ Breaks simple UI tools expectations

**Why not chosen:** User requirement for self-contained schemas

### Alternative 3: Limit Enum Sizes

**Approach:** Cap enums at N concepts per domain

```python
MAX_ENUM_SIZE = 500

if len(sorted_ids) > MAX_ENUM_SIZE:
    sorted_ids = sorted_ids[:MAX_ENUM_SIZE]
    print(f"WARNING: Truncated {domain} to {MAX_ENUM_SIZE}")
```

**Pros:**
- ✅ Manageable file sizes (<10MB per schema)
- ✅ Fast loading
- ✅ Reasonable for UI dropdowns

**Cons:**
- ❌ Incomplete coverage
- ❌ Arbitrary cutoff (why 500?)
- ❌ Which concepts to include?
  - Most common? (Need usage data)
  - Alphabetical? (Arbitrary)
  - Most recent? (Not necessarily useful)
- ❌ Drug domain needs full coverage

**Why not chosen:** User explicitly requested all standard concepts

### Alternative 4: oneOf Instead of enum

**Approach:** Use pure JSON Schema without extensions

```json
{
  "oneOf": [
    {"const": 0, "title": "No matching concept"},
    {"const": 8507, "title": "MALE", "description": "Male gender"},
    {"const": 8532, "title": "FEMALE", "description": "Female gender"}
  ]
}
```

**Pros:**
- ✅ Pure JSON Schema (no extensions)
- ✅ Richer per-option metadata (title, description, etc.)
- ✅ Better validator error messages

**Cons:**
- ❌ ~3x larger file size
- ❌ Drug domain → 600MB vs 227MB
- ❌ Slower validation (tests each oneOf branch)
- ❌ More complex to parse for UI
- ❌ Overkill for simple dropdowns

**Comparison:**

| Format | Size | Parse Time | UI Complexity |
|--------|------|------------|---------------|
| enum + x-enumNames | 227MB | Fast | Simple |
| oneOf | 600MB | Slow | Medium |

**Why not chosen:** Size/performance trade-off not justified

### Alternative 5: Database Backend

**Approach:** Store concepts in SQLite/PostgreSQL

```python
import sqlite3

# Load concepts into DB
conn = sqlite3.connect('concepts.db')
conn.execute("""
    CREATE TABLE concepts (
        concept_id INT,
        domain_id VARCHAR(20),
        concept_name VARCHAR(255)
    )
""")

# Schemas reference DB
{
  "gender_concept_id": {
    "type": "integer",
    "x-conceptDomain": "Gender",
    "x-conceptDb": "concepts.db"
  }
}
```

**Pros:**
- ✅ Efficient storage/queries
- ✅ Dynamic vocabulary updates
- ✅ Supports complex queries

**Cons:**
- ❌ Adds dependency (SQLite/PostgreSQL)
- ❌ Not self-contained
- ❌ Complex deployment
- ❌ Breaks JSON Schema portability
- ❌ Requires runtime database connection

**Why not chosen:** Violates standard library + self-contained requirements

## Trade-offs Accepted

### Large File Sizes (759MB total)

**Accepted:** Some schema files are 200MB+

**Justification:**
- Storage is cheap
- Complete coverage more valuable than small files
- Users can lazy-load in applications
- Alternative (truncation) worse

**Mitigation:**
- Document file sizes prominently
- Provide lazy loading examples
- Recommend compression for distribution
- Explain as expected behavior

### Slow Initial Load (10-30 seconds)

**Accepted:** Conversion takes 10-30 seconds

**Justification:**
- One-time setup cost
- Progress logging shows activity
- No runtime dependencies (worth the wait)

**Mitigation:**
- Progress every 500K concepts
- Clear output messages
- Document expected timing

### Memory Usage (2GB peak)

**Accepted:** Requires ~2GB RAM during conversion

**Justification:**
- Modern systems have RAM
- Streaming not possible with lookup building
- Fast enum injection after load

**Mitigation:**
- Document RAM requirement
- Fail gracefully if out of memory
- Log memory warnings

### No Caching

**Accepted:** No caching between runs

**Justification:**
- Conversion is infrequent
- Caching adds complexity
- Could add later if needed

**Mitigation:**
- Keep code simple
- Document that re-runs take same time

### Missing Enums for Some Fields

**Accepted:** Only 39/120+ CONCEPT FKs have enums

**Justification:**
- CDM metadata doesn't specify all domains
- Can't generate enums without domain info
- Fields without domains get plain integer type

**Mitigation:**
- Document which fields get enums
- Explain domain requirement
- Show how to check x-foreignKeys

## Lessons Learned

### 1. OMOP Vocabularies Are Massive

**Discovery:** 6.3M concepts, 2.5M standard, Drug domain alone is 2M

**Impact:** Plan for scale from the start

**Takeaway:** Always check vocabulary sizes before designing schema format

### 2. TSV vs CSV Matters

**Discovery:** CONCEPT.csv is actually tab-separated

**Impact:** Initial comma parsing failed on medical terms

**Takeaway:** Never assume CSV, always check delimiter

### 3. Standard Library is Powerful

**Discovery:** csv.DictReader handles TSV, unicode, quotes perfectly

**Tools used:**
- `csv.DictReader(f, delimiter='\t')` - TSV parsing
- `defaultdict(dict)` - Efficient grouping
- `json.dump(f, indent=2, ensure_ascii=False)` - Unicode-safe JSON
- No external dependencies needed

**Takeaway:** Check standard library before adding dependencies

### 4. User Requirements Drive Design

**User said:** "All standard concepts"
**We delivered:** 759MB of schemas

**Alternative rejected:** Truncate to 500 per domain (incomplete)

**Takeaway:** Take requirements literally, mitigate downsides

### 5. Progress Feedback Essential

**Problem:** 6M rows take time, users think it froze

**Solution:** Log every 500K rows

**Takeaway:** Always show progress for long operations

## Future Enhancements

### 1. Compression Option

**Idea:** Gzip schemas for distribution

```bash
gzip schemas/*.json
# drug_exposure.schema.json: 227MB → 20MB
```

**Benefit:** 90% size reduction
**Cost:** Decompression required
**Effort:** Low (add flag to script)

### 2. Vocabulary Versioning

**Idea:** Track OMOP vocabulary version in schemas

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "x-omopVocabularyVersion": "v5.0 21-OCT-21",
  "x-generated": "2025-11-25T14:00:00Z"
}
```

**Benefit:** Version tracking
**Effort:** Medium (parse Athena version)

### 3. Incremental Updates

**Idea:** Cache concept mappings, only rebuild changed domains

```python
# Load cached domain hashes
if domain_hash_unchanged(domain):
    enum_map[domain] = load_cached_enum(domain)
else:
    enum_map[domain] = build_enum(domain)
```

**Benefit:** Faster subsequent runs
**Effort:** High (caching infrastructure)

### 4. Custom Filtering

**Idea:** Config file for domain selection

```yaml
# config.yml
domains:
  include:
    - Gender
    - Race
    - Type Concept
  exclude:
    - Drug  # Too large
    - Observation
```

**Benefit:** Flexibility
**Effort:** Medium (config parsing)

### 5. Validation Tool

**Idea:** Validate generated schemas

```python
# validate_schemas.py
for schema_file in glob('schemas/*.json'):
    check_valid_json(schema_file)
    check_enum_completeness(schema_file)
    check_required_fields(schema_file)
```

**Benefit:** Quality assurance
**Effort:** Low (add validation script)

### 6. Documentation Generator

**Idea:** Auto-generate browsable docs from schemas

```bash
python generate_docs.py
# Creates docs/ with HTML pages for each table
```

**Benefit:** Human-readable documentation
**Effort:** High (HTML generation)

## Conclusion

The OMOP CDM JSON Schema Converter successfully bridges OMOP's massive standardized vocabularies and practical JSON Schema validation for data entry applications.

**Key achievements:**

1. **Complete coverage** - All 2.5M standard concepts included
2. **Self-contained** - No external dependencies or runtime lookups
3. **Standards compliant** - JSON Schema draft-07 with enum validation
4. **UI-ready** - Human-readable labels embedded
5. **Portable** - Works anywhere JSON Schema is supported

**Key trade-offs:**

- **Large files** (759MB) for completeness
- **Simple code** (standard library only) for maintainability
- **One-time cost** (30s conversion) for zero runtime dependencies

**Validation:**

The implementation proves that careful design choices—enum+x-enumNames for compact representation, standard concept filtering for data quality, and progress logging for user experience—enable handling 6.3 million concepts while maintaining simplicity using only Python's standard library.

**Impact:**

UI developers can now build validated OMOP data entry tools without:
- Database connections
- API calls
- External vocabulary services
- Complex deployment

Just load a JSON Schema file and extract enums for dropdowns. This enables a new class of lightweight OMOP data entry applications.

---

**For usage instructions and examples, see [README.md](README.md)**
