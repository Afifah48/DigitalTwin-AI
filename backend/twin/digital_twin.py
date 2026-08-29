import json
import csv
from typing import Optional, List, Dict, Callable
from ..models.states import FactoryState, TelemetryState
from ..models.events import FactoryEvent
from ..models.enums import StationId
from ..config.factory_config import FactoryConfig, get_default_factory_config
from ..simulation.engine import FactoryEngine


class DigitalTwin:
    """
    Automotive Production Digital Twin Core Simulator.
    Encapsulates the discrete-event simulation engine, event stream, and telemetry models.
    """

    def __init__(
        self,
        config: Optional[FactoryConfig] = None,
        seed: Optional[int] = None,
        event_callback: Optional[Callable[[FactoryEvent], None]] = None,
    ):
        self.config = config or get_default_factory_config()
        self.seed = seed
        self.event_callback = event_callback
        self.engine = FactoryEngine(
            config=self.config,
            seed=self.seed,
            event_callback=self.event_callback,
        )

    def reset(self, config: Optional[FactoryConfig] = None, seed: Optional[int] = None):
        """Resets the digital twin to initial state."""
        if config is not None:
            self.config = config
        if seed is not None:
            self.seed = seed
        self.engine = FactoryEngine(
            config=self.config,
            seed=self.seed,
            event_callback=self.event_callback,
        )

    def simulate(self, duration_seconds: float) -> FactoryState:
        """Runs the simulation for duration_seconds and returns the final FactoryState."""
        return self.engine.run(duration_seconds)

    def step_until(self, target_time_seconds: float) -> FactoryState:
        """Advances simulation to target_time_seconds and returns current FactoryState."""
        self.engine.step_until(target_time_seconds)
        return self.engine.get_factory_state()

    def get_state(self) -> FactoryState:
        """Returns the current factory state."""
        return self.engine.get_factory_state()

    def get_events(self) -> List[FactoryEvent]:
        """Returns all recorded discrete events."""
        return self.engine.events

    def get_telemetry_snapshot(self) -> Dict[StationId, TelemetryState]:
        """Returns a snapshot of all station telemetry."""
        state = self.engine.get_factory_state()
        return {st_id: st.telemetry for st_id, st in state.stations.items()}

    def export_event_log_json(self, filepath: str):
        """Exports recorded discrete events to a JSON file for machine learning datasets."""
        events_dict = [event.model_dump(mode="json") for event in self.engine.events]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(events_dict, f, indent=2)

    def export_event_log_csv(self, filepath: str):
        """Exports recorded discrete events to a structured CSV file."""
        if not self.engine.events:
            return

        fieldnames = [
            "timestamp",
            "event_type",
            "station_id",
            "buffer_id",
            "vehicle_id",
            "cycle_time",
            "machine_state",
            "queue_before",
            "queue_after",
            "buffer_before",
            "buffer_after",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for event in self.engine.events:
                row = {
                    "timestamp": event.timestamp,
                    "event_type": event.event_type.value if hasattr(event.event_type, "value") else event.event_type,
                    "station_id": event.station_id.value if event.station_id else None,
                    "buffer_id": event.buffer_id.value if event.buffer_id else None,
                    "vehicle_id": event.vehicle_id,
                    "cycle_time": event.cycle_time,
                    "machine_state": event.machine_state.value if event.machine_state else None,
                    "queue_before": event.queue_before,
                    "queue_after": event.queue_after,
                    "buffer_before": event.buffer_before,
                    "buffer_after": event.buffer_after,
                }
                writer.writerow(row)


# Alias for FactorySimulator
FactorySimulator = DigitalTwin
