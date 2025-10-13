"""Base entity for ActronAir Neo integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.helpers.entity import EntityCategory  # type: ignore
from homeassistant.helpers.update_coordinator import CoordinatorEntity  # type: ignore

from .const import DOMAIN
from .coordinator import ActronDataCoordinator

_LOGGER = logging.getLogger(__name__)

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
        """
        Initialize the base entity.
        
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

        # Performance optimization: track last known state for change detection
        self._last_state_hash: int | None = None
        self._last_attributes_hash: int | None = None

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

    def _calculate_state_hash(self, state_data: Any) -> int:
        """
        Calculate hash for state change detection.

        Args:
            state_data: State data to hash

        Returns:
            Hash value for change detection

        """
        try:
            # Convert to string and hash for change detection
            if state_data is None:
                return hash(None)
            if isinstance(state_data, (dict, list)):
                # For complex objects, use string representation
                return hash(str(sorted(state_data.items()) if isinstance(state_data, dict) else state_data))
            return hash(state_data)
        except (TypeError, AttributeError):
            # Fallback for unhashable types
            return hash(str(state_data))

    def _has_state_changed(self, new_state: Any) -> bool:
        """
        Check if state has changed since last update.

        Args:
            new_state: New state value

        Returns:
            True if state has changed

        """
        new_hash = self._calculate_state_hash(new_state)
        if self._last_state_hash != new_hash:
            self._last_state_hash = new_hash
            return True
        return False

    def _has_attributes_changed(self, new_attributes: dict[str, Any] | None) -> bool:
        """
        Check if attributes have changed since last update.

        Args:
            new_attributes: New attributes dict

        Returns:
            True if attributes have changed

        """
        new_hash = self._calculate_state_hash(new_attributes)
        if self._last_attributes_hash != new_hash:
            self._last_attributes_hash = new_hash
            return True
        return False

    def should_update_state(self, new_state: Any, new_attributes: dict[str, Any] | None = None) -> bool:
        """
        Determine if entity state should be updated.

        This method provides performance optimization by avoiding unnecessary
        state updates when neither state nor attributes have changed.

        Args:
            new_state: New state value
            new_attributes: New attributes dict

        Returns:
            True if state should be updated

        """
        state_changed = self._has_state_changed(new_state)
        attributes_changed = self._has_attributes_changed(new_attributes) if new_attributes is not None else False

        if state_changed or attributes_changed:
            _LOGGER.debug(
                "Entity %s state update: state_changed=%s, attributes_changed=%s",
                self.entity_id, state_changed, attributes_changed
            )
            return True

        return False
