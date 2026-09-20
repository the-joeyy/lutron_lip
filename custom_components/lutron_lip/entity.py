"""Base class for Lutron devices."""

from collections.abc import Callable, Mapping
import re
from typing import Any

from homeassistant.const import ATTR_IDENTIFIERS
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .aiolip import Device, KeypadComponent, LutronController, Output, Sysvar
from .const import DOMAIN, KEYPAD_DEVICE_TYPE_NAMES, link_to_controller


_GENERIC_COMPONENT_NAME = re.compile(r"^(?:btn|led|cci)\s+\d+$", re.IGNORECASE)


def _name_starts_with_area(name: str, area_name: str) -> bool:
    """Return True if name already starts with the area name."""
    name = name.strip()
    area_name = area_name.strip()
    if not name or not area_name:
        return False

    name_lower = name.casefold()
    area_lower = area_name.casefold()
    if name_lower == area_lower:
        return True
    if not name_lower.startswith(area_lower):
        return False

    next_char = name[len(area_name) : len(area_name) + 1]
    return next_char in {" ", "-", "_", "/", ":", "."}


def _normalise_area_prefixed_name(name: str, area_name: str) -> str:
    """Return a consistently dashed name when it already starts with area."""
    name = name.strip()
    area_name = area_name.strip()
    if name.casefold() == area_name.casefold():
        return area_name

    tail = name[len(area_name) :].strip()
    tail = tail.lstrip(" -_/:.").strip()
    if not tail:
        return area_name
    return f"{area_name} - {tail}"


def _with_area_prefix(name: str, area_name: str, raw_area_name: str | None = None) -> str:
    """Prefix name with area unless it already includes that area."""
    if not area_name:
        return name
    if _name_starts_with_area(name, area_name):
        return _normalise_area_prefixed_name(name, area_name)
    if raw_area_name and _name_starts_with_area(name, raw_area_name):
        return _normalise_area_prefixed_name(name, raw_area_name)
    return f"{area_name} - {name}"


def _is_meaningful_component_name(name: str | None, fallback: str) -> bool:
    """Return True if a keypad component name is better than Btn/Led/CCI N."""
    if not name:
        return False
    name = name.strip()
    if not name or name.casefold().startswith("unknown button"):
        return False
    return not _GENERIC_COMPONENT_NAME.fullmatch(name) or name.casefold() != fallback.casefold()


class LutronBaseEntity(Entity):
    """Base class for Lutron entities.

    The entity represents a device in the Lutron system.
    The entity is associated with a device with device_name.
    The entity has no name, the name is from the device
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name: str | None = None

    def __init__(
        self,
        lutron_device: Device,
        controller: LutronController,
    ) -> None:
        """Initialize the device."""
        self._lutron_device = lutron_device
        self._controller = controller
        self._attr_device_info = link_to_controller(
            DeviceInfo(
                identifiers={(DOMAIN, self.unique_id)},
                manufacturer="Lutron",
                name=self.device_name,
                suggested_area=self.area_name if controller.suggest_areas else None,
            ),
            controller.guid,
            getattr(controller, "ha_device_id", None),
        )

    @property
    def area_name(self) -> str:
        """Return the area name."""
        if (area := self._lutron_device.area) is not None:
            return (
                area.name
                if not self._controller.use_full_path
                else f"{area.location} {area.name}"
            )
        return ""

    @property
    def device_name(self) -> str:
        """Return the device name including the computed area_name."""
        if (lutron_device := self._lutron_device) is not None:
            if self._controller.use_area_for_device_name:
                raw_area_name = (
                    lutron_device.area.name
                    if getattr(lutron_device, "area", None) is not None
                    else None
                )
                return _with_area_prefix(
                    lutron_device.name,
                    self.area_name,
                    raw_area_name,
                )
            return lutron_device.name
        return "No Name"

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self._controller.subscribe(
            self._lutron_device.integration_id, None, self._update_callback
        )

    async def async_update(self) -> None:
        """Update the entity's state. It's called after async_added."""
        await self._request_state()

    async def _request_state(self) -> None:
        """Request the state."""

    def _update_callback(self, value) -> None:
        """Handle Lutron messages for this integration_id."""

    async def async_will_remove_from_hass(self) -> None:
        """Unregister the entity."""
        await self._controller.stop()

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        if self._lutron_device.uuid is None:
            return f"{self._controller.guid}_{self._lutron_device.legacy_uuid}"
        return f"{self._controller.guid}_{self._lutron_device.uuid}"

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the state attributes."""
        return {"lutron_integration_id": self._lutron_device.integration_id}

    async def _execute_device_command(
        self, command_method: Callable, *args, **kwargs
    ) -> None:
        """Execute a command from the device.

        Takes a device method (like self._lutron_device.set_level)
        and its arguments, creates the command, and executes it through the controller.
        """
        command = command_method(*args, **kwargs)
        await self._controller.execute_command(command)


class LutronOutput(LutronBaseEntity):
    """Representation of a Lutron output device entity."""

    _lutron_device: Output


class LutronVariable(LutronBaseEntity):
    """Representation of a Lutron variable entity.

    It's connected to the controller device.
    """

    _lutron_device: Sysvar

    def __init__(
        self,
        lutron_device: Device,
        controller: LutronController,
    ) -> None:
        """Initialize the entity with the proper name. Assign it to the controller device."""
        super().__init__(lutron_device, controller)
        self._attr_name = lutron_device.name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, controller.guid)},
        )


class LutronKeypadComponent(LutronBaseEntity):
    """Representation of a Lutron Keypad Component, such as Leds, Buttons, Events.

    The HA device is the keypad with device_name
    The entity has a name, so the full name is device_name + name
    """

    _lutron_device: KeypadComponent

    def __init__(
        self,
        lutron_device: KeypadComponent,
        controller: LutronController,
    ) -> None:
        """Initialize the device.

        RadioRA main repeater is also a keypad.
        HomeworksQS is not.
        """
        super().__init__(lutron_device, controller)
        self._component_number = lutron_device.component_number
        keypad = lutron_device.keypad
        model = KEYPAD_DEVICE_TYPE_NAMES.get(keypad.device_type, keypad.device_type)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._lutron_device.integration_id))},
            manufacturer="Lutron",
            name=self.device_name,
            model=model,
            serial_number=keypad.serial_number,
            suggested_area=self.area_name if controller.suggest_areas else None,
        )
        if lutron_device.keypad.device_type == "MAIN_REPEATER":
            self._attr_device_info[ATTR_IDENTIFIERS].add((DOMAIN, controller.guid))
        else:
            self._attr_device_info = link_to_controller(
                self._attr_device_info,
                controller.guid,
                getattr(controller, "ha_device_id", None),
            )

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        fallback = self._lutron_device.component_name
        if _is_meaningful_component_name(self._lutron_device.name, fallback):
            return self._lutron_device.name
        return fallback

    @property
    def keypad_name(self) -> str:
        """Return the keypad name.

        If we are using radiora mode, we use the keypad name, not the device_group_name.
        Usually the keypad device in the DB doesn't have a meaningful name (e.g., CDS 001 for international keypads).
        """
        if self._controller.use_radiora_mode:
            return self._lutron_device.keypad.name
        if self._lutron_device.keypad.device_group_name:
            return self._lutron_device.keypad.device_group_name
        return f"keypad {self._lutron_device.keypad.integration_id}"

    @property
    def device_name(self) -> str:
        """Return the keypad device name including the computed area_name."""
        if self._controller.use_area_for_device_name:
            raw_area_name = (
                self._lutron_device.area.name
                if getattr(self._lutron_device, "area", None) is not None
                else None
            )
            return _with_area_prefix(
                self.keypad_name,
                self.area_name,
                raw_area_name,
            )
        return self.keypad_name

    async def async_added_to_hass(self) -> None:  # pylint: disable=hass-missing-super-call
        """Register the keypad component using also the component_number to get the updates for the components."""
        self._controller.subscribe(
            self._lutron_device.integration_id,
            self._component_number,
            self._update_callback,
        )


class LutronControllerBaseEntity(Entity):
    """Representation of the controller entity."""

    _attr_has_entity_name = True

    def __init__(self, controller: LutronController) -> None:
        """Initialize the controller entity."""
        self._controller = controller
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, controller.guid)},
            name="Lutron Controller",
            manufacturer="Lutron",
            model=controller.lip.controller_type.name.lower(),
            sw_version="NA",
        )

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._controller.guid
