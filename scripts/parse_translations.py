#!/usr/bin/env python3
"""
Parse translations from translations.telegram.org for tdesktop.
Extracts approved translations for a given language with full pagination.
"""

import re
import sys
import time
import urllib.request
import html as html_module
from collections import OrderedDict

SECTIONS = [
    "login",
    "chat_list",
    "private_chats",
    "groups_and_channels",
    "profile",
    "settings",
    "stories",
    "camera_and_media",
    "bots_and_payments",
    "passport",
    "general",
    "unsorted",
]

BASE_URL = "https://translations.telegram.org"
PAGE_SIZE = 200


def fetch_page(url):
    """Fetch a URL and return HTML content"""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}", file=sys.stderr)
        return ""


def clean_value(text):
    """Clean HTML entities and tags from value text"""
    text = re.sub(r'<mark[^>]*>', '', text)
    text = re.sub(r'</mark>', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = html_module.unescape(text)
    text = text.strip()
    return text


def extract_value_from_block(block_html, lang):
    """Extract key and value(s) from a single tr-key-row-wrap block.

    Returns list of (key, value) tuples (multiple for plurals).
    """
    results = []

    # Extract key
    key_match = re.search(r'data-key="([^"]+)"', block_html)
    if not key_match:
        return results
    key = key_match.group(1)

    if lang == "en":
        # For English: extract from tr-value-default
        value_block = re.search(
            r'<div\s+class="tr-value-default">(.*?)</div>\s*<div\s+class="tr-value-key">',
            block_html, re.DOTALL
        )
    else:
        # For other languages: extract approved translation
        # The approved translation is in <div class="tr-value"> (NOT tr-value-suggestion)
        # It appears inside tr-value-suggestions section
        value_block = re.search(
            r'<div\s+class="tr-value"><a\s+class="tr-value-link"[^>]*>(.*?)</a>\s*</div>',
            block_html, re.DOTALL
        )

    if not value_block:
        return results

    value_html = value_block.group(1)

    # Check if pluralized
    if 'class="pluralized"' in value_html:
        plural_pattern = re.compile(
            r'<span\s+class="p-value"\s+data-label="([^"]+)">\s*<span\s+class="value">(.*?)</span>',
            re.DOTALL
        )
        for pm in plural_pattern.finditer(value_html):
            label = pm.group(1)
            value = clean_value(pm.group(2))
            results.append((f"{key}#{label}", value))
    else:
        value_match = re.search(
            r'<span\s+class="value">(.*?)</span>',
            value_html, re.DOTALL
        )
        if value_match:
            value = clean_value(value_match.group(1))
            results.append((key, value))

    return results


def parse_page_html(page_html, lang):
    """Parse a single page of HTML by splitting into blocks."""
    translations = OrderedDict()

    # Split by tr-key-row-wrap boundaries
    blocks = re.split(r'<div\s+class="tr-key-row-wrap">', page_html)

    for block in blocks[1:]:  # Skip the first part (before first entry)
        pairs = extract_value_from_block(block, lang)
        for key, value in pairs:
            translations[key] = value

    return translations


def get_total_phrases(page_html):
    """Extract total phrase count from page"""
    m = re.search(r'(\d+)\s+phrases', page_html)
    if m:
        return int(m.group(1))
    return 0


def parse_section_full(lang, section):
    """Parse a full section with pagination"""
    all_trans = OrderedDict()

    url = f"{BASE_URL}/{lang}/tdesktop/{section}/"
    print(f"  Fetching {section} (page 1)...", file=sys.stderr, end="", flush=True)
    page_html = fetch_page(url)
    if not page_html:
        print(" FAILED", file=sys.stderr)
        return all_trans

    total = get_total_phrases(page_html)
    trans = parse_page_html(page_html, lang)
    all_trans.update(trans)
    print(f" {len(trans)} keys (total: {total} phrases)", file=sys.stderr)

    offset = PAGE_SIZE
    page_num = 2
    while offset < total:
        time.sleep(0.3)
        url = f"{BASE_URL}/{lang}/tdesktop/{section}/?offset={offset}"
        print(f"  Fetching {section} (page {page_num}, offset={offset})...", file=sys.stderr, end="", flush=True)
        page_html = fetch_page(url)
        if not page_html:
            print(" FAILED", file=sys.stderr)
            break

        trans = parse_page_html(page_html, lang)
        if not trans:
            print(" 0 keys (stopping)", file=sys.stderr)
            break

        all_trans.update(trans)
        print(f" {len(trans)} keys", file=sys.stderr)

        offset += PAGE_SIZE
        page_num += 1

    return all_trans


def parse_all_sections(lang):
    """Parse all sections for a language"""
    all_translations = OrderedDict()

    for section in SECTIONS:
        section_trans = parse_section_full(lang, section)
        print(f"  => Section '{section}': {len(section_trans)} translations", file=sys.stderr)
        all_translations.update(section_trans)
        time.sleep(0.3)

    return all_translations


def write_strings_file(translations, output_path, lang_name):
    """Write translations in .strings format"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write('/*\n')
        f.write('This file is part of BeHappy Desktop,\n')
        f.write('the official desktop application for the BeHappy messaging service.\n')
        f.write('*/\n')
        f.write(f'"lng_language_name" = "{lang_name}";\n')

        for key, value in translations.items():
            if key == "lng_language_name":
                continue
            escaped = value.replace('\\', '\\\\').replace('"', '\\"')
            escaped = escaped.replace('\n', '\\n')
            f.write(f'"{key}" = "{escaped}";\n')

    print(f"\nWrote {len(translations)} translations to {output_path}", file=sys.stderr)


def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else "ru"
    output = sys.argv[2] if len(sys.argv) > 2 else f"/tmp/tdesktop_lang_{lang}.strings"

    lang_names = {
        "ru": "Русский",
        "en": "English",
        "uk": "Українська",
        "de": "Deutsch",
        "fr": "Français",
        "es": "Español",
    }

    print(f"Parsing translations for '{lang}'...", file=sys.stderr)
    translations = parse_all_sections(lang)
    print(f"\nTotal: {len(translations)} translations parsed", file=sys.stderr)

    lang_name = lang_names.get(lang, lang)
    write_strings_file(translations, output, lang_name)

    print(f"\n=== Summary ===", file=sys.stderr)
    print(f"Language: {lang}", file=sys.stderr)
    print(f"Total keys: {len(translations)}", file=sys.stderr)
    print(f"Output: {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
