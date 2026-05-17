"""Lutron event types (kept for backward compatibility)."""

from enum import StrEnum


class LutronEventType(StrEnum):
    """Lutron event types fired on the lutron_event bus."""

    PRESS = "press"
    RELEASE = "release"
    HOLD = "hold"
    DOUBLE_TAP = "double_tap"
    HOLD_RELEASE = "hold_release"
