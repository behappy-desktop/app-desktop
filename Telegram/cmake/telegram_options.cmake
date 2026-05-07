# This file is part of Telegram Desktop,
# the official desktop application for the Telegram messaging service.
#
# For license and copyright information please follow this link:
# https://github.com/telegramdesktop/tdesktop/blob/master/LEGAL

# BeHappy: API credentials (server doesn't validate these)
set(TDESKTOP_API_ID 1)
set(TDESKTOP_API_HASH "stub")

# BeHappy: always disable autoupdate and crash reports (no Telegram servers)
target_compile_definitions(Telegram PRIVATE TDESKTOP_DISABLE_AUTOUPDATE)
target_compile_definitions(Telegram PRIVATE TDESKTOP_DISABLE_CRASH_REPORTS)

if (DESKTOP_APP_USE_PACKAGED)
    target_compile_definitions(Telegram PRIVATE TDESKTOP_USE_PACKAGED)
endif()

if (DESKTOP_APP_SPECIAL_TARGET)
    target_compile_definitions(Telegram PRIVATE TDESKTOP_ALLOW_CLOSED_ALPHA)
endif()
