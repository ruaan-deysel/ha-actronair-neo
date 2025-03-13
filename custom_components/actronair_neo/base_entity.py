"""Base entity for ActronAir Neo integration."""
from __future__ import annotations

from homeassistant.helpers.entity import EntityCategory # type: ignore
from homeassistant.helpers.update_coordinator import CoordinatorEntity # type: ignore

from .const import DOMAIN
from .coordinator import ActronDataCoordinator

class ActronEntityBase(CoordinatorEntity):
    """Base class for all ActronAir Neo entities."""

    DEVICE_NAME = "ActronAir Neo"

    def __init__(
        self,
        coordinator: ActronDataCoordinator,
        entity_type: str,
        name_suffix: str = "",
        is_diagnostic: bool = False,
    ) -> None:
        """Initialize the base entity.
        
        Args:
            coordinator: The data coordinator
            entity_type: Type of entity (climate, sensor, etc.)
            name_suffix: Optional suffix for the entity name
            is_diagnostic: Whether this is a diagnostic entity
        """
        super().__init__(coordinator)
        self._attr_has_entity_name = True

        # Set entity category for diagnostic entities
        if is_diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

        # Generate consistent unique_id
        base_unique_id = f"{coordinator.device_id}_{entity_type}"
        self._attr_unique_id = (
            f"{base_unique_id}_{name_suffix.lower().replace(' ', '_')}"
            if name_suffix else base_unique_id
        )

        # Set consistent name
        self._attr_name = name_suffix if name_suffix else self.DEVICE_NAME

    @property
    def device_info(self):
        """Return device information."""
        coordinator_data = self.coordinator.data
        if isinstance(coordinator_data, dict):
            return {
                "identifiers": {(DOMAIN, self.coordinator.device_id)},
                "name": self.DEVICE_NAME,
                "manufacturer": "ActronAir",
                "model": coordinator_data.get("main", {}).get("model"),
                "sw_version": coordinator_data.get("main", {}).get("firmware_version"),
            }
        return None
