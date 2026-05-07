#!/usr/bin/env python3
"""
Merge official tdesktop lang.strings with BeHappy customizations,
and generate Russian translation file from parsed data.
"""

import re
import sys
from collections import OrderedDict


# BeHappy-specific overrides for English
BEHAPPY_EN_OVERRIDES = {
    "lng_open_from_tray": "Open BeHappy",
    "lng_quit_from_tray": "Quit BeHappy",
    "lng_tray_icon_text": "BeHappy is still running here,\\nyou can change this in Settings.\\nIf it disappears from the tray,\\nyou can drag it back from the hidden icons.",
    "lng_intro_qr_step1": "Open BeHappy on your phone",
}

# BeHappy-specific overrides for Russian
BEHAPPY_RU_OVERRIDES = {
    "lng_open_from_tray": "Открыть BeHappy",
    "lng_quit_from_tray": "Закрыть BeHappy",
    "lng_tray_icon_text": "BeHappy всё ещё работает,\\nВы можете изменить это в настройках.\\nЕсли значок исчезнет из трея,\\nВы можете ��еретащить его обратно из скрытых значков.",
    "lng_intro_qr_step1": "Откройте BeHappy на телефоне",
}

# Manual translations for the 11 keys missing from the website
MANUAL_RU_TRANSLATIONS = {
    "lng_profile_unofficial_warning": "{icon} {name} использует неофициальный клиент Telegram — с��общения этому пользователю могут быть менее защищены.",
    "lng_proxy_box_check_status": "Проверить статус",
    "lng_proxy_box_table_available": "Доступен (пинг: {ping} мс)",
    "lng_proxy_box_table_button": "Подключить прокси",
    "lng_proxy_box_table_checking": "Проверка…",
    "lng_proxy_box_table_title": "Прокси-сервер",
    "lng_proxy_box_table_unavailable": "Недоступен",
    "lng_proxy_check_ip_proceed": "Продолжить",
    "lng_proxy_check_ip_warning": "Ваш IP-адрес будет виден администратору прокси-сервера.",
    "lng_proxy_check_ip_warning_title": "Предупреждение",
    "lng_send_as_file_tooltip": "Отправить текст как файл.",
}


def parse_strings_file(filepath):
    """Parse a .strings file into OrderedDict and preserve the raw lines for structure."""
    translations = OrderedDict()
    lines = []

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            lines.append(line.rstrip('\n'))
            # Parse key = value
            m = re.match(r'^"([^"]+)"\s*=\s*"(.*)";$', line.strip())
            if m:
                key = m.group(1)
                value = m.group(2)
                translations[key] = value

    return translations, lines


def write_merged_en(official_path, output_path, overrides):
    """Take the official lang.strings and apply BeHappy overrides."""
    with open(official_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    with open(output_path, "w", encoding="utf-8") as f:
        for line in lines:
            m = re.match(r'^("([^"]+)"\s*=\s*")(.*)(";\s*)$', line)
            if m:
                key = m.group(2)
                if key in overrides:
                    f.write(f'{m.group(1)}{overrides[key]}{m.group(4)}\n')
                    continue
                # Replace "Telegram" standalone references with "BeHappy" in specific keys
                if key in ("lng_settings_auto_start", "lng_settings_add_sendto"):
                    new_val = m.group(3).replace("Telegram", "BeHappy")
                    f.write(f'{m.group(1)}{new_val}{m.group(4)}\n')
                    continue
            f.write(line)

    print(f"Wrote EN lang.strings to {output_path}")


def build_ru_file(official_en_path, parsed_ru_path, output_path):
    """Build a complete Russian translation file.

    Uses the official EN file as the structure template.
    For each key: use parsed RU translation, or manual, or fall back to EN.
    """
    # Parse all sources
    en_trans, en_lines = parse_strings_file(official_en_path)
    ru_trans, _ = parse_strings_file(parsed_ru_path)

    # Apply manual translations
    for key, val in MANUAL_RU_TRANSLATIONS.items():
        if key not in ru_trans:
            ru_trans[key] = val

    # Apply BeHappy overrides
    for key, val in BEHAPPY_RU_OVERRIDES.items():
        ru_trans[key] = val

    # Also translate some specific keys
    ru_trans["lng_settings_auto_start"] = ru_trans.get("lng_settings_auto_start", "Запускать BeHappy при запуске системы")
    if "lng_settings_auto_start" in ru_trans:
        ru_trans["lng_settings_auto_start"] = ru_trans["lng_settings_auto_start"].replace("Telegram", "BeHappy")
    if "lng_settings_add_sendto" in ru_trans:
        ru_trans["lng_settings_add_sendto"] = ru_trans["lng_settings_add_sendto"].replace("Telegram", "BeHappy")

    # Set language name
    ru_trans["lng_language_name"] = "Русский"
    ru_trans["lng_switch_to_this"] = "Продолжить на русском"

    # Write following EN structure, adding extra plural forms from RU
    covered = 0
    missing = 0
    missing_keys = []
    written_keys = set()

    with open(output_path, "w", encoding="utf-8") as f:
        for line in en_lines:
            m = re.match(r'^("([^"]+)"\s*=\s*")(.*)(";\s*)$', line.rstrip())
            if m:
                key = m.group(2)
                if key in ru_trans:
                    val = ru_trans[key]
                    f.write(f'"{key}" = "{val}";\n')
                    covered += 1
                    written_keys.add(key)

                    # After writing a plural form, also emit extra RU forms
                    # (e.g., after #other, emit #few and #many if not in EN)
                    if '#' in key:
                        base_key = key.rsplit('#', 1)[0]
                        # Check for additional RU plural forms not in EN
                        for label in ('zero', 'one', 'two', 'few', 'many', 'other'):
                            extra_key = f"{base_key}#{label}"
                            if extra_key in ru_trans and extra_key not in written_keys and extra_key not in en_trans:
                                f.write(f'"{extra_key}" = "{ru_trans[extra_key]}";\n')
                                written_keys.add(extra_key)
                                covered += 1
                else:
                    # Keep English as fallback
                    f.write(line.rstrip() + '\n')
                    missing += 1
                    missing_keys.append(key)
                    written_keys.add(key)
            elif line.strip().startswith('/*') or line.strip().startswith('*') or line.strip().startswith('//') or line.strip() == '':
                # Preserve comments and blank lines
                f.write(line.rstrip() + '\n')
            else:
                f.write(line.rstrip() + '\n')

    print(f"\nRussian translation stats:")
    print(f"  Covered: {covered}/{covered + missing} ({100*covered/(covered+missing):.1f}%)")
    print(f"  Missing (EN fallback): {missing}")
    if missing_keys:
        print(f"  Missing keys: {', '.join(missing_keys[:20])}")
        if len(missing_keys) > 20:
            print(f"  ... and {len(missing_keys) - 20} more")


def main():
    official_en = sys.argv[1] if len(sys.argv) > 1 else "/tmp/tdesktop_lang_en.strings"
    parsed_ru = sys.argv[2] if len(sys.argv) > 2 else "/tmp/tdesktop_lang_ru.strings"
    out_en = sys.argv[3] if len(sys.argv) > 3 else "Telegram/Resources/langs/lang.strings"
    out_ru = sys.argv[4] if len(sys.argv) > 4 else "Telegram/Resources/langs/lang_ru.strings"

    print("=== Generating English lang.strings ===")
    write_merged_en(official_en, out_en, BEHAPPY_EN_OVERRIDES)

    print("\n=== Generating Russian lang_ru.strings ===")
    build_ru_file(official_en, parsed_ru, out_ru)


if __name__ == "__main__":
    main()
