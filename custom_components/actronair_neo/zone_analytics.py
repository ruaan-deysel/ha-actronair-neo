"""Zone analytics and monitoring for ActronAir Neo integration."""
from __future__ import annotations

import json
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

class ZoneUsageStats:
    """Zone usage statistics."""

    def __init__(self, zone_id: str):
        """Initialize zone usage stats.

        Args:
            zone_id: Zone identifier
        """
        self.zone_id = zone_id
        self.total_runtime_hours = 0.0
        self.daily_runtime_hours: Dict[str, float] = {}  # date -> hours
        self.temperature_history: deque = deque(maxlen=1440)  # 24 hours of minute data
        self.setpoint_changes = 0
        self.on_off_cycles = 0
        self.last_state_change = None
        self.efficiency_score = 0.0
        
    def record_temperature(self, temp: float, setpoint: float, timestamp: Optional[datetime] = None) -> None:
        """Record temperature reading.
        
        Args:
            temp: Current temperature
            setpoint: Target temperature
            timestamp: Reading timestamp
        """
        if timestamp is None:
            timestamp = dt_util.utcnow()
            
        self.temperature_history.append({
            "timestamp": timestamp,
            "temperature": temp,
            "setpoint": setpoint,
            "variance": abs(temp - setpoint) if setpoint else 0,
        })
        
    def record_state_change(self, new_state: bool, timestamp: Optional[datetime] = None) -> None:
        """Record zone state change.
        
        Args:
            new_state: New zone state (on/off)
            timestamp: Change timestamp
        """
        if timestamp is None:
            timestamp = dt_util.utcnow()
            
        if self.last_state_change is not None:
            # Calculate runtime if zone was on
            if self.last_state_change.get("state"):
                runtime = (timestamp - self.last_state_change["timestamp"]).total_seconds() / 3600
                self.total_runtime_hours += runtime
                
                # Add to daily stats
                date_key = timestamp.date().isoformat()
                self.daily_runtime_hours[date_key] = self.daily_runtime_hours.get(date_key, 0) + runtime
                
        self.last_state_change = {"state": new_state, "timestamp": timestamp}
        self.on_off_cycles += 1
        
    def record_setpoint_change(self) -> None:
        """Record a setpoint change."""
        self.setpoint_changes += 1
        
    def calculate_efficiency_score(self) -> float:
        """Calculate zone efficiency score (0-100).

        Returns:
            Efficiency score based on temperature variance and cycling
        """
        if not self.temperature_history:
            return 0.0

        # Calculate average temperature variance
        variances = [reading["variance"] for reading in self.temperature_history if reading["variance"] is not None]
        if not variances:
            return 0.0

        avg_variance = sum(variances) / len(variances)

        # Score based on temperature control (lower variance = higher score)
        temp_score = max(0.0, 100.0 - (avg_variance * 20))  # 5°C variance = 0 score

        # Penalty for excessive cycling (more than 10 cycles per day is poor)
        cycle_penalty = min(50, self.on_off_cycles * 5) if self.on_off_cycles > 10 else 0

        self.efficiency_score = max(0.0, temp_score - cycle_penalty)
        return self.efficiency_score


        
    def get_daily_runtime(self, date: datetime) -> float:
        """Get runtime hours for a specific date.
        
        Args:
            date: Date to query
            
        Returns:
            Runtime hours for the date
        """
        date_key = date.date().isoformat()
        return self.daily_runtime_hours.get(date_key, 0.0)
        
    def get_recent_temperature_trend(self, hours: int = 24) -> Dict[str, Any]:
        """Get recent temperature trend analysis.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Temperature trend analysis
        """
        cutoff_time = dt_util.utcnow() - timedelta(hours=hours)
        recent_readings = [
            reading for reading in self.temperature_history
            if reading["timestamp"] >= cutoff_time
        ]
        
        if not recent_readings:
            return {"status": "no_data"}
            
        temperatures = [r["temperature"] for r in recent_readings if r["temperature"] is not None]
        variances = [r["variance"] for r in recent_readings if r["variance"] is not None]
        
        if not temperatures:
            return {"status": "no_data"}
            
        return {
            "status": "ok",
            "avg_temperature": sum(temperatures) / len(temperatures),
            "min_temperature": min(temperatures),
            "max_temperature": max(temperatures),
            "avg_variance": sum(variances) / len(variances) if variances else 0,
            "readings_count": len(recent_readings),
            "stability": "stable" if max(temperatures) - min(temperatures) < 2 else "variable",
        }

class ZoneAnalyticsManager:
    """Manages zone analytics and performance monitoring."""

    def __init__(self, hass: HomeAssistant, device_id: str):
        """Initialize analytics manager.

        Args:
            hass: Home Assistant instance
            device_id: Device identifier
        """
        self.hass = hass
        self.device_id = device_id
        self._zone_stats: Dict[str, ZoneUsageStats] = {}
        # Use Home Assistant's Store for async file operations
        self._store = Store(hass, 1, f"actron_zone_analytics_{device_id}")
        
    async def async_load(self) -> None:
        """Load analytics data from storage."""
        try:
            # Use Home Assistant's Store for async file operations
            data = await self._store.async_load()

            if data is not None:
                for zone_id, zone_data in data.get("zones", {}).items():
                    stats = ZoneUsageStats(zone_id)
                    stats.total_runtime_hours = zone_data.get("total_runtime_hours", 0.0)
                    stats.daily_runtime_hours = zone_data.get("daily_runtime_hours", {})
                    stats.setpoint_changes = zone_data.get("setpoint_changes", 0)
                    stats.on_off_cycles = zone_data.get("on_off_cycles", 0)
                    stats.efficiency_score = zone_data.get("efficiency_score", 0.0)

                    # Load last state change
                    if zone_data.get("last_state_change"):
                        try:
                            stats.last_state_change = {
                                "state": zone_data["last_state_change"]["state"],
                                "timestamp": datetime.fromisoformat(zone_data["last_state_change"]["timestamp"])
                            }
                        except (ValueError, KeyError):
                            pass

                    self._zone_stats[zone_id] = stats

                _LOGGER.debug("Loaded analytics for %d zones", len(self._zone_stats))
            else:
                _LOGGER.debug("No existing analytics data found for device %s", self.device_id)
        except Exception as err:
            _LOGGER.error("Failed to load zone analytics: %s", err)
            
    async def async_save(self) -> None:
        """Save analytics data to storage."""
        try:
            data = {"zones": {}}

            for zone_id, stats in self._zone_stats.items():
                zone_data = {
                    "total_runtime_hours": stats.total_runtime_hours,
                    "daily_runtime_hours": stats.daily_runtime_hours,
                    "setpoint_changes": stats.setpoint_changes,
                    "on_off_cycles": stats.on_off_cycles,
                    "efficiency_score": stats.efficiency_score,
                }

                if stats.last_state_change:
                    zone_data["last_state_change"] = {
                        "state": stats.last_state_change["state"],
                        "timestamp": stats.last_state_change["timestamp"].isoformat()
                    }

                data["zones"][zone_id] = zone_data

            # Use Home Assistant's Store for async file operations
            await self._store.async_save(data)

            _LOGGER.debug("Saved zone analytics for device %s", self.device_id)
        except Exception as err:
            _LOGGER.error("Failed to save zone analytics: %s", err)
            
    def get_zone_stats(self, zone_id: str) -> ZoneUsageStats:
        """Get or create zone statistics.

        Args:
            zone_id: Zone identifier

        Returns:
            Zone usage statistics
        """
        if zone_id not in self._zone_stats:
            self._zone_stats[zone_id] = ZoneUsageStats(zone_id)
        return self._zone_stats[zone_id]
        
    async def async_record_zone_data(
        self,
        zone_id: str,
        temperature: Optional[float],
        setpoint: Optional[float],
        is_enabled: bool,
    ) -> None:
        """Record zone data for analytics.
        
        Args:
            zone_id: Zone identifier
            temperature: Current temperature
            setpoint: Target temperature
            is_enabled: Zone enabled state
        """
        stats = self.get_zone_stats(zone_id)
        
        # Record temperature if available
        if temperature is not None and setpoint is not None:
            stats.record_temperature(temperature, setpoint)
            
        # Check for state changes
        if stats.last_state_change is None or stats.last_state_change["state"] != is_enabled:
            stats.record_state_change(is_enabled)
            
        # Calculate efficiency score periodically
        stats.calculate_efficiency_score()
        
    async def async_record_setpoint_change(self, zone_id: str) -> None:
        """Record a setpoint change for analytics.
        
        Args:
            zone_id: Zone identifier
        """
        stats = self.get_zone_stats(zone_id)
        stats.record_setpoint_change()
        
    def get_system_summary(self) -> Dict[str, Any]:
        """Get system-wide analytics summary.
        
        Returns:
            System analytics summary
        """
        if not self._zone_stats:
            return {"status": "no_data"}
            
        total_runtime = sum(stats.total_runtime_hours for stats in self._zone_stats.values())
        avg_efficiency = sum(stats.efficiency_score for stats in self._zone_stats.values()) / len(self._zone_stats)
        total_cycles = sum(stats.on_off_cycles for stats in self._zone_stats.values())
        
        # Find most and least used zones
        most_used = max(self._zone_stats.items(), key=lambda x: x[1].total_runtime_hours)
        least_used = min(self._zone_stats.items(), key=lambda x: x[1].total_runtime_hours)
        
        return {
            "status": "ok",
            "total_zones": len(self._zone_stats),
            "total_runtime_hours": total_runtime,
            "average_efficiency_score": avg_efficiency,
            "total_on_off_cycles": total_cycles,
            "most_used_zone": {"id": most_used[0], "runtime": most_used[1].total_runtime_hours},
            "least_used_zone": {"id": least_used[0], "runtime": least_used[1].total_runtime_hours},
        }
        
    def get_zone_performance_report(self, zone_id: str) -> Dict[str, Any]:
        """Get detailed performance report for a zone.
        
        Args:
            zone_id: Zone identifier
            
        Returns:
            Zone performance report
        """
        if zone_id not in self._zone_stats:
            return {"status": "no_data"}
            
        stats = self._zone_stats[zone_id]
        recent_trend = stats.get_recent_temperature_trend()
        
        # Calculate daily average for last 7 days
        recent_daily_avg = 0.0
        recent_days = 0
        cutoff_date = dt_util.now().date() - timedelta(days=7)
        
        for date_str, hours in stats.daily_runtime_hours.items():
            try:
                date = datetime.fromisoformat(date_str).date()
                if date >= cutoff_date:
                    recent_daily_avg += hours
                    recent_days += 1
            except ValueError:
                continue
                
        if recent_days > 0:
            recent_daily_avg /= recent_days
            
        return {
            "status": "ok",
            "zone_id": zone_id,
            "total_runtime_hours": stats.total_runtime_hours,
            "recent_daily_average_hours": recent_daily_avg,
            "efficiency_score": stats.efficiency_score,
            "setpoint_changes": stats.setpoint_changes,
            "on_off_cycles": stats.on_off_cycles,
            "temperature_trend": recent_trend,
            "performance_rating": self._get_performance_rating(stats.efficiency_score),
        }
        
    def _get_performance_rating(self, efficiency_score: float) -> str:
        """Get performance rating based on efficiency score.
        
        Args:
            efficiency_score: Efficiency score (0-100)
            
        Returns:
            Performance rating string
        """
        if efficiency_score >= 80:
            return "excellent"
        elif efficiency_score >= 60:
            return "good"
        elif efficiency_score >= 40:
            return "fair"
        else:
            return "poor"
