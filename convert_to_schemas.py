#!/usr/bin/env python3
"""
OMOP CDM 5.4 to JSON Schema Converter
Converts OMOP Common Data Model CSV to individual JSON Schema draft-07 files
"""

import csv
import json
import os
import re
import sys
from collections import defaultdict


def is_na(value):
    """Check if value is NA/null/empty"""
    if not value:
        return True
    return value.strip().upper() in ('NA', 'NULL', '')


def parse_datatype(datatype):
    """
    Parse OMOP datatype into base type and max length
    Returns: (base_type, max_length)
    Examples:
        'varchar(50)' -> ('varchar', 50)
        'varchar(MAX)' -> ('varchar', None)
        'integer' -> ('integer', None)
    """
    if not datatype:
        return (None, None)

    datatype = datatype.strip()

    # Check for varchar with length
    match = re.match(r'^varchar\s*\((\d+|MAX)\)$', datatype, re.IGNORECASE)
    if match:
        length_str = match.group(1)
        max_length = None if length_str.upper() == 'MAX' else int(length_str)
        return ('varchar', max_length)

    # Return base type without length
    return (datatype.lower(), None)


def map_to_json_type(datatype):
    """
    Map OMOP datatype to JSON Schema type object
    Returns: dict with type, format, and optionally maxLength
    """
    base_type, max_length = parse_datatype(datatype)

    if not base_type:
        return {"type": "string"}

    type_map = {
        'integer': {"type": "integer"},
        'float': {"type": "number"},
        'date': {"type": "string", "format": "date"},
        'datetime': {"type": "string", "format": "date-time"},
        'varchar': {"type": "string"}
    }

    schema_type = type_map.get(base_type, {"type": "string"})

    # Add maxLength for varchar with specified length
    if base_type == 'varchar' and max_length is not None:
        schema_type = schema_type.copy()
        schema_type['maxLength'] = max_length

    return schema_type


def build_description(user_guidance, etl_conventions):
    """Combine userGuidance and etlConventions into description with labels"""
    parts = []

    if not is_na(user_guidance):
        parts.append(f"User Guidance: {user_guidance.strip()}")

    if not is_na(etl_conventions):
        parts.append(f"ETL Conventions: {etl_conventions.strip()}")

    if not parts:
        return None

    # Join with double newline for readability
    return '\n\n'.join(parts)


def load_csv_data(csv_path):
    """Load CSV data into list of dictionaries"""
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def group_by_table(rows):
    """Group CSV rows by cdmTableName"""
    tables = defaultdict(list)
    for row in rows:
        table_name = row.get('cdmTableName', '').strip()
        if table_name:
            tables[table_name].append(row)
    return dict(tables)


def load_concept_data(concept_csv_path):
    """
    Load CONCEPT.csv and build domain -> concepts mapping
    Returns: {domain: {concept_id: concept_name, ...}}
    """
    concepts_by_domain = defaultdict(dict)

    print(f"Loading CONCEPT vocabulary from {concept_csv_path}...")
    with open(concept_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        count = 0
        for row in reader:
            count += 1
            if count % 500000 == 0:
                print(f"  Loaded {count:,} concepts...")

            concept_id = row.get('concept_id', '').strip()
            concept_name = row.get('concept_name', '').strip()
            domain_id = row.get('domain_id', '').strip()
            standard_concept = row.get('standard_concept', '').strip()

            # Filter to standard concepts only
            if standard_concept != 'S' and concept_id != '0':
                continue

            if concept_id and concept_name and domain_id:
                try:
                    concepts_by_domain[domain_id][int(concept_id)] = concept_name
                except ValueError:
                    continue

    print(f"  Loaded {count:,} total concepts")
    print(f"  Found {len(concepts_by_domain)} domains")
    return dict(concepts_by_domain)


def build_concept_enum_mapping(concept_data):
    """
    Convert concept data to oneOf format
    Returns: {domain: oneOf_array}
    """
    enum_map = {}

    for domain, concepts in concept_data.items():
        # Always ensure concept_id 0 is included
        if 0 not in concepts:
            concepts[0] = "No matching concept"

        # Sort concept IDs
        sorted_ids = sorted(concepts.keys())

        # Build oneOf array with const and title
        one_of_array = []
        for concept_id in sorted_ids:
            concept_name = concepts[concept_id]
            one_of_array.append({
                "const": concept_id,
                "title": f"{concept_id} - {concept_name}"
            })

        enum_map[domain] = one_of_array

        # Log info for large domains
        if len(sorted_ids) > 1000:
            print(f"  INFO: Domain '{domain}' has {len(sorted_ids):,} concepts")

    return enum_map


def build_table_schema(table_name, fields, concept_enum_map=None):
    """
    Build complete JSON Schema for a table
    fields: list of CSV row dicts for this table
    concept_enum_map: optional dict mapping domain to oneOf array
    """
    properties = {}
    required = []
    primary_keys = []
    foreign_keys = []

    for field in fields:
        field_name = field.get('cdmFieldName', '').strip()
        if not field_name:
            continue

        # Build property schema
        prop_schema = map_to_json_type(field.get('cdmDatatype', ''))

        # Add description
        description = build_description(
            field.get('userGuidance', ''),
            field.get('etlConventions', '')
        )
        if description:
            prop_schema['description'] = description

        # Track foreign keys and add enums for CONCEPT references
        if field.get('isForeignKey', '').strip().upper() == 'YES':
            fk_table = field.get('fkTableName', '').strip()
            fk_field = field.get('fkFieldName', '').strip()
            fk_domain = field.get('fkDomain', '').strip()

            if fk_table and not is_na(fk_table):
                fk_obj = {
                    "field": field_name,
                    "table": fk_table,
                    "fieldInTable": fk_field
                }

                # Add domain if present
                if fk_domain and not is_na(fk_domain):
                    fk_obj['domain'] = fk_domain

                    # Add oneOf for CONCEPT foreign keys
                    if fk_table.upper() == 'CONCEPT' and concept_enum_map and fk_domain in concept_enum_map:
                        one_of_array = concept_enum_map[fk_domain]
                        prop_schema['oneOf'] = one_of_array

                foreign_keys.append(fk_obj)

        properties[field_name] = prop_schema

        # Track required fields
        if field.get('isRequired', '').strip().upper() == 'YES':
            required.append(field_name)

        # Track primary keys
        if field.get('isPrimaryKey', '').strip().upper() == 'YES':
            primary_keys.append(field_name)

    # Build complete schema
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": table_name.replace('_', ' ').title(),
        "type": "object",
        "properties": properties
    }

    # Add required array if present
    if required:
        schema['required'] = required

    # Add x-primaryKey array if present
    if primary_keys:
        schema['x-primaryKey'] = primary_keys

    # Add x-foreignKeys array if present
    if foreign_keys:
        schema['x-foreignKeys'] = foreign_keys

    return schema


def write_schema_file(table_name, schema, output_dir):
    """Write schema to JSON file"""
    filename = f"{table_name}.schema.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    return filepath


def main():
    """Main conversion process"""
    csv_path = 'data/OMOP_CDMv5.4_Field_Level.csv'
    concept_csv_path = 'data/CONCEPT.csv'
    output_dir = 'schemas'

    # Validate CSV exists
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    # Load CSV data
    print(f"Loading CSV from {csv_path}...")
    rows = load_csv_data(csv_path)
    print(f"Loaded {len(rows)} rows")

    # Group by table
    print("Grouping by table...")
    tables = group_by_table(rows)
    print(f"Found {len(tables)} tables")

    # Load CONCEPT data if available
    concept_enum_map = None
    if os.path.exists(concept_csv_path):
        try:
            concept_data = load_concept_data(concept_csv_path)
            print("Building oneOf mappings...")
            concept_enum_map = build_concept_enum_mapping(concept_data)
            print(f"Built oneOf constraints for {len(concept_enum_map)} domains")
        except Exception as e:
            print(f"WARNING: Failed to load CONCEPT.csv: {e}")
            print("Continuing without oneOf generation...")
    else:
        print(f"INFO: CONCEPT.csv not found at {concept_csv_path}")
        print("Schemas will be generated without oneOf constraints")

    # Generate schemas
    print("\nGenerating schemas...")
    for table_name, fields in sorted(tables.items()):
        schema = build_table_schema(table_name, fields, concept_enum_map)
        filepath = write_schema_file(table_name, schema, output_dir)
        print(f"  ✓ {table_name} ({len(fields)} fields)")

    print(f"\nSuccess! Generated {len(tables)} schema files in {output_dir}/")


if __name__ == '__main__':
    main()
