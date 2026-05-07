#!/usr/bin/env python3
"""
Convert .strings translation file to JSON format used by bh-mvsy langpack system.
Handles plural forms: key#one, key#few etc → {"key": {"one": "...", "few": "..."}}
"""

import re
import json
import sys
from collections import OrderedDict


def parse_strings_file(filepath):
    """Parse a .strings file, returning ordered list of (key, value) tuples."""
    entries = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r'^"([^"]+)"\s*=\s*"(.*)";$', line.strip())
            if m:
                key = m.group(1)
                value = m.group(2)
                # Unescape
                value = value.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                entries.append((key, value))
    return entries


def convert_to_json(entries):
    """Convert entries to JSON dict with proper plural grouping."""
    result = OrderedDict()

    for key, value in entries:
        if '#' in key:
            # Plural form: key#label → grouped
            base_key, label = key.rsplit('#', 1)
            if base_key not in result:
                result[base_key] = OrderedDict()
            if isinstance(result[base_key], str):
                # Key exists as non-plural, convert
                result[base_key] = OrderedDict({"other": result[base_key]})
            result[base_key][label] = value
        else:
            result[key] = value

    return result


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "/tmp/tdesktop_lang_ru.strings"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "/tmp/desktop_ru.json"

    entries = parse_strings_file(input_file)
    print(f"Parsed {len(entries)} entries from {input_file}", file=sys.stderr)

    json_data = convert_to_json(entries)
    print(f"Generated {len(json_data)} JSON keys", file=sys.stderr)

    # Count plurals
    plural_count = sum(1 for v in json_data.values() if isinstance(v, dict))
    single_count = len(json_data) - plural_count
    print(f"  Singles: {single_count}, Plurals: {plural_count}", file=sys.stderr)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    print(f"Wrote to {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
