"""Lutron constants."""

DOMAIN = "lutron_lip"

# Configuration keys
CONF_REFRESH_DATA = "refresh_data"
CONF_USE_FULL_PATH = "use_full_path"
CONF_USE_AREA_FOR_DEVICE_NAME = "use_area_for_device_name"
CONF_VARIABLE_IDS = "variable_ids"
CONF_USE_RADIORA_MODE = "use_radiora_mode"
CONF_SUGGEST_AREAS = "suggest_areas"

# Connection settings
CONF_CONNECTION_TIMEOUT = "connection_timeout"
CONF_RETRY_ATTEMPTS = "retry_attempts"
CONF_RETRY_DELAY = "retry_delay"
CONF_HEARTBEAT_INTERVAL = "heartbeat_interval"
CONF_DEBUG_MODE = "debug_mode"

# File paths
LUTRON_DATA_FILE = "lutron_data.xml"

# Device settings
CONF_DEFAULT_DIMMER_LEVEL = "default_dimmer_level"

# Default values
DEFAULT_DIMMER_LEVEL = 255
DEFAULT_CONNECTION_TIMEOUT = 30
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY = 5.0
DEFAULT_HEARTBEAT_INTERVAL = 60
DEFAULT_DEBUG_MODE = False

# Connection states
CONNECTION_STATE_CONNECTED = "connected"
CONNECTION_STATE_DISCONNECTED = "disconnected"
CONNECTION_STATE_CONNECTING = "connecting"

# Human-readable names for Lutron keypad device types (used in DeviceInfo model field)
KEYPAD_DEVICE_TYPE_NAMES: dict[str, str] = {
    "PHANTOM": "Phantom Keypad",
    "HWI_SEETOUCH_KEYPAD": "HWI SeeTouch Keypad",
    "SEETOUCH_KEYPAD": "SeeTouch Keypad",
    "SEETOUCH_TABLETOP_KEYPAD": "SeeTouch Tabletop Keypad",
    "PICO_KEYPAD": "Pico Keypad",
    "HYBRID_SEETOUCH_KEYPAD": "Hybrid SeeTouch Keypad",
    "MAIN_REPEATER": "Main Repeater",
    "HOMEOWNER_KEYPAD": "Homeowner Keypad",
    "INTERNATIONAL_SEETOUCH_KEYPAD": "International SeeTouch Keypad",
    "WCI": "WCI",
    "QS_IO_INTERFACE": "QS IO Interface",
    "GRAFIK_T_HYBRID_KEYPAD": "GRAFIK T Hybrid Keypad",
    "HWI_SLIM": "HWI Slim Keypad",
    "PALLADIOM_KEYPAD": "Palladiom Keypad",
    "GRAFIK_EYE_QS": "GRAFIK Eye QS",
}

# Device types
DEVICE_TYPE_LIGHT = "light"
DEVICE_TYPE_COVER = "cover"
DEVICE_TYPE_FAN = "fan"
DEVICE_TYPE_SWITCH = "switch"
DEVICE_TYPE_KEYPAD = "keypad"
DEVICE_TYPE_BUTTON = "button"
DEVICE_TYPE_LED = "led"
DEVICE_TYPE_SENSOR = "sensor"
DEVICE_TYPE_VARIABLE = "variable"

# Error messages
ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_INVALID_AUTH = "invalid_auth"
ERROR_TIMEOUT = "timeout"
ERROR_UNKNOWN = "unknown"
ERROR_DATABASE_LOAD = "database_load"
ERROR_DEVICE_NOT_FOUND = "device_not_found"


# ── Parenting entities to the controller device ─────────────────────────────
# Ctrlable Pro 2026.9 dropped DeviceInfo's `via_device` (a parent *identifier*
# tuple) for `via_device_id` (the parent's device-registry id), and the old
# spelling now raises instead of warning. A `via_device` riding inside an
# entity's DeviceInfo is the exposed case: by the time core calls
# async_get_or_create no frame of ours is left on the stack, so HA cannot
# attribute the call to a custom integration and applies core behaviour —
# ReportBehavior.ERROR — which aborts the entity at add time.
#
# `async_get_device` is deprecated for the same release family (identifiers are
# no longer unique across config entries); `async_get_devices` replaces it.
#
# Probe rather than pin, so one build serves cores either side of the change.
from homeassistant.helpers.device_registry import DeviceInfo as _DeviceInfo

_SUPPORTS_VIA_DEVICE_ID = "via_device_id" in getattr(
    _DeviceInfo, "__annotations__", {}
)


def link_to_controller(info, controller_guid, controller_device_id=None):
    """Parent a DeviceInfo to the Lutron controller, however this core spells it."""
    if _SUPPORTS_VIA_DEVICE_ID:
        if controller_device_id:
            info["via_device_id"] = controller_device_id
    else:
        info["via_device"] = (DOMAIN, controller_guid)
    return info


def first_device_by_identifier(dev_reg, identifiers: set):
    """First device matching any of ``identifiers``, without async_get_device."""
    getter = getattr(dev_reg, "async_get_devices", None)
    if getter is not None:
        matches = getter(identifiers=identifiers)
    else:
        matches = [
            d for d in dev_reg.devices.values() if set(d.identifiers) & identifiers
        ]
    return matches[0] if matches else None
