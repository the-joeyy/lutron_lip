"""Support for Lutron events."""

from enum import StrEnum

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DOMAIN, LutronData
from .aiolip import Button, LutronController
from .entity import LutronKeypadComponent


class LutronEventType(StrEnum):
    """Lutron event types."""

    PRESS = "press"
    RELEASE = "release"
    HOLD = "hold"
    DOUBLE_TAP = "double_tap"
    HOLD_RELEASE = "hold_release"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Lutron event platform."""
    entry_data: LutronData = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        LutronEventEntity(button, entry_data.controller)
        for button in entry_data.buttons
    )


class LutronEventEntity(LutronKeypadComponent, EventEntity):
    """Representation of a Lutron keypad button as an HA event entity.

    Updates the event.* entity state on button press/release. The lutron_event
    bus is fired separately by _setup_button_events() in __init__.py.
    """

    _lutron_device: Button
    _attr_translation_key = "button"
    action_number_to_event = {
        3: LutronEventType.PRESS,
        4: LutronEventType.RELEASE,
        5: LutronEventType.HOLD,
        6: LutronEventType.DOUBLE_TAP,
        32: LutronEventType.HOLD_RELEASE,
    }

    def __init__(
        self,
        button: Button,
        controller: LutronController,
    ) -> None:
        """Initialize the button."""
        super().__init__(button, controller)
        self._attr_name = self.name
        self._attr_event_types = [
            LutronEventType.PRESS,
            LutronEventType.RELEASE,
            LutronEventType.HOLD,
            LutronEventType.HOLD_RELEASE,
            LutronEventType.DOUBLE_TAP,
        ]

    def _update_callback(self, value: int) -> None:
        """Update the event.* entity state on button action."""
        event = self.action_number_to_event.get(value)
        if event:
            self._trigger_event(event)
