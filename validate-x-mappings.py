#!/usr/bin/env python3
"""
Validate x-mappings in QUADRIGA schema files against the meta-schema.

This script validates that all x-mappings definitions in JSON schema files
located in directories starting with 'v' (e.g., v1.0.0/) comply with the
x-mappings meta-schema defined in x-mappings-meta-schema.json.

Requirements:
  - Python 3.9+ (uses only standard library)
  - No external dependencies

Usage:
  python3 validate-x-mappings.py

Exit codes:
  0 - All x-mappings are valid
  1 - Validation errors found or script error

Integration:
  This script is automatically run by build-html.sh as a sanity check
  before generating HTML documentation.
"""

import json
import re
import sys
from pathlib import Path


def load_json_file(filepath: Path) -> dict[str, object]:
    """Load and parse a JSON file."""
    try:
        with filepath.open(encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {filepath}: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"ERROR: Cannot read {filepath}: {e}", file=sys.stderr)
        sys.exit(1)


def load_context_namespaces(version_dir: Path) -> set[str]:
    """Load the valid namespaces from @context in the root schema.json file.

    Args:
        version_dir: The version directory (e.g., Path('v1.0.0'))

    Returns:
        Set of valid namespace prefixes (e.g., {'dc', 'dcterms', 'lrmi', ...})
    """
    schema_file = version_dir / "schema.json"
    if not schema_file.exists():
        return set()

    schema = load_json_file(schema_file)
    context = schema.get("@context", {})

    if not isinstance(context, dict):
        return set()

    return set(context.keys())


def validate_mapping_entry(
    entry: object, vocab: str, valid_namespaces: set[str]
) -> list[str]:
    """Validate a single mapping entry against the meta-schema rules.

    Args:
        entry: The mapping entry to validate
        vocab: The vocabulary identifier for error messages (e.g., "schema[0]", "dc")
        valid_namespaces: Set of valid namespace prefixes from @context
    """
    errors = []

    # Must be null or an object
    if entry is None:
        return errors

    if not isinstance(entry, dict):
        errors.append(f"  {vocab}: must be null or an object, got {type(entry).__name__}")
        return errors

    # Check required properties
    if "relation" not in entry:
        errors.append(f"  {vocab}: missing required property 'relation'")
    if "target" not in entry:
        errors.append(f"  {vocab}: missing required property 'target'")

    # Check for additional properties
    allowed_props = {"$comment", "relation", "target"}
    extra_props = set(entry.keys()) - allowed_props
    if extra_props:
        errors.append(f"  {vocab}: unexpected properties {extra_props}")

    # Validate relation enum
    if "relation" in entry:
        valid_relations = [
            "skos:exactMatch",
            "skos:closeMatch",
            "skos:broadMatch",
            "skos:narrowMatch",
            "skos:relatedMatch",
        ]
        if not isinstance(entry["relation"], str):
            errors.append(f"  {vocab}.relation: must be a string")
        elif entry["relation"] not in valid_relations:
            errors.append(
                f"  {vocab}.relation: invalid value '{entry['relation']}', "
                f"must be one of {valid_relations}"
            )

    # Validate target pattern - allow both namespace:term format and full URIs
    if "target" in entry:
        if not isinstance(entry["target"], str):
            errors.append(f"  {vocab}.target: must be a string")
        else:
            target = entry["target"]
            # Check if it's a URI
            if target.startswith("http://") or target.startswith("https://"):
                # Full URI is allowed
                pass
            elif ":" in target:
                # namespace:term format - validate namespace is from @context
                namespace, _, term = target.partition(":")
                if not term:
                    errors.append(
                        f"  {vocab}.target: '{target}' is missing the term part after ':'"
                    )
                elif namespace not in valid_namespaces:
                    errors.append(
                        f"  {vocab}.target: namespace '{namespace}' in '{target}' is not defined in @context. "
                        f"Valid namespaces: {sorted(valid_namespaces)}"
                    )
                elif not re.match(r"^[a-zA-Z]+$", term):
                    errors.append(
                        f"  {vocab}.target: term '{term}' in '{target}' must contain only letters"
                    )
            else:
                errors.append(
                    f"  {vocab}.target: '{target}' must be either a namespace:term format "
                    f"(e.g., 'dc:title') or a full URI (e.g., 'https://...')"
                )

    return errors


def validate_x_mappings(x_mappings: object, valid_namespaces: set[str]) -> list[str]:
    """Validate x-mappings object against the meta-schema.

    Args:
        x_mappings: The x-mappings object to validate
        valid_namespaces: Set of valid namespace prefixes from @context
    """
    errors = []

    if not isinstance(x_mappings, dict):
        errors.append(f"x-mappings must be an object, got {type(x_mappings).__name__}")
        return errors

    # Check required vocabularies
    required_vocabs = ["amb", "dc", "dcat", "dcterms", "hermes", "lrmi", "modalia", "schema"]
    missing_vocabs = [vocab for vocab in required_vocabs if vocab not in x_mappings]
    errors.extend(f"Missing required vocabulary: {vocab}" for vocab in missing_vocabs)

    # Check for additional vocabularies (allow $comment for documentation)
    allowed_keys = set(required_vocabs) | {"$comment"}
    extra_vocabs = set(x_mappings.keys()) - allowed_keys
    if extra_vocabs:
        errors.append(f"Unexpected vocabularies: {extra_vocabs}")

    # Validate each mapping entry (can be null, object, or array of objects)
    for vocab in required_vocabs:
        if vocab in x_mappings:
            entry = x_mappings[vocab]

            # Handle array of mappings
            if isinstance(entry, list):
                if len(entry) == 0:
                    errors.append(f"{vocab}: array must have at least 1 item")
                for idx, mapping in enumerate(entry):
                    entry_errors = validate_mapping_entry(
                        mapping, f"{vocab}[{idx}]", valid_namespaces
                    )
                    errors.extend(entry_errors)
            else:
                # Handle single mapping (object or null)
                entry_errors = validate_mapping_entry(entry, vocab, valid_namespaces)
                errors.extend(entry_errors)

    return errors


def find_schema_files() -> list[Path]:
    """Find all JSON schema files in directories starting with 'v'."""
    # Find all directories starting with 'v'
    schema_files = [
        json_file
        for version_dir in Path().glob("v*")
        if version_dir.is_dir()
        for json_file in version_dir.glob("*.json")
    ]

    return sorted(schema_files)


def main() -> int:
    """Validate x-mappings in QUADRIGA schema files."""
    print("Validating x-mappings in QUADRIGA schema files...\n")

    schema_files = find_schema_files()

    if not schema_files:
        print("No schema files found in directories starting with 'v'")
        return 0

    print(f"Found {len(schema_files)} schema files to check\n")

    total_errors = 0
    files_with_mappings = 0
    files_validated = 0

    # Group files by version directory and load @context once per version
    files_by_version: dict[Path, list[Path]] = {}
    for filepath in schema_files:
        version_dir = filepath.parent
        if version_dir not in files_by_version:
            files_by_version[version_dir] = []
        files_by_version[version_dir].append(filepath)

    # Process each version directory
    for version_dir, filepaths in sorted(files_by_version.items()):
        # Load valid namespaces from @context once per version
        valid_namespaces = load_context_namespaces(version_dir)
        if not valid_namespaces:
            print(
                f"⚠️  Warning: No @context found in {version_dir}/schema.json, "
                f"skipping namespace validation for this version"
            )
            print()

        # Validate each file in this version
        for filepath in filepaths:
            schema = load_json_file(filepath)

            # Check if this schema has x-mappings
            if "x-mappings" not in schema:
                continue

            files_with_mappings += 1
            errors = validate_x_mappings(schema["x-mappings"], valid_namespaces)

            if errors:
                print(f"❌ {filepath}:")
                for error in errors:
                    print(f"  {error}")
                print()
                total_errors += len(errors)
            else:
                files_validated += 1

    # Summary
    print("=" * 60)
    print("Validation complete:")
    print(f"  Files checked: {len(schema_files)}")
    print(f"  Files with x-mappings: {files_with_mappings}")
    print(f"  Files validated successfully: {files_validated}")
    print(f"  Files with errors: {files_with_mappings - files_validated}")
    print(f"  Total errors: {total_errors}")
    print("=" * 60)

    if total_errors > 0:
        print("\n❌ Validation FAILED")
        return 1

    print("\n✅ All x-mappings are valid!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
