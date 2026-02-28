"""Base entity for ActronAir Neo integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import (
    DeviceInfo,  # type: ignore[import-untyped]
)
from homeassistant.helpers.entity import EntityCategory  # type: ignore[import-untyped]
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,  # type: ignore[import-untyped]
)

from .const import DEVICE_MANUFACTURER, DOMAIN

if TYPE_CHECKING:
    from .coordinator import ActronDataCoordinator


class ActronAirNeoEntity(CoordinatorEntity["ActronDataCoordinator"]):
    """Base class for all ActronAir Neo entities."""

    _attr_has_entity_name = True
    _attr_attribution = "Data provided by ActronAir Neo"

    DEVICE_NAME = "ActronAir Neo"

    def __init__(
        self,
        coordinator: ActronDataCoordinator,
        entity_type: str,
        name_suffix: str = "",
        *,
        is_diagnostic: bool = False,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)

        if is_diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

        # Generate consistent unique_id.
        base_unique_id = f"{coordinator.device_id}_{entity_type}"
        self._attr_unique_id = (
            f"{base_unique_id}_{name_suffix.lower().replace(' ', '_')}"
            if name_suffix
            else base_unique_id
        )

        # Set entity name — name_suffix becomes the entity name part.
        # When has_entity_name is True, HA prefixes the device name automatically.
        self._attr_name = name_suffix or None

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device information."""
        coordinator_data = self.coordinator.data
        if isinstance(coordinator_data, dict):
            main_data = coordinator_data.get("main", {})
            return DeviceInfo(
                identifiers={(DOMAIN, self.coordinator.device_id)},
                name=self.DEVICE_NAME,
                manufacturer=DEVICE_MANUFACTURER,
                model=main_data.get("model"),
                serial_number=self.coordinator.device_id,
                sw_version=main_data.get("firmware_version"),
            )
        return None
