from typing import Callable, Optional, List
import simpy
import numpy as np
from ..models.enums import VehicleModel, EventType
from ..models.states import VehicleState
from ..models.events import FactoryEvent


MODEL_PRESETS = [
    {"model": VehicleModel.APEX_GT_EV, "color": "#38BDF8", "color_name": "Cyber Blue"},
    {"model": VehicleModel.NEXUS_SEDAN, "color": "#E2E8F0", "color_name": "Polar Silver"},
    {"model": VehicleModel.VALENCE_SUV, "color": "#94A3B8", "color_name": "Titanium Graphite"},
    {"model": VehicleModel.HORIZON_CROSS, "color": "#F59E0B", "color_name": "Solar Flare"},
]


class VehicleGenerator:
    """
    Simulates input feeder releasing vehicle bodies into S1 queue according to takt time.
    Supports dynamic arrival interval modification for upstream surge scenarios.
    """

    def __init__(
        self,
        env: simpy.Environment,
        output_queue: simpy.Store,
        arrival_interval: float = 54.0,
        arrival_std: float = 0.0,
        event_logger: Optional[Callable[[FactoryEvent], None]] = None,
        rng: Optional[np.random.Generator] = None,
        max_vehicles: Optional[int] = None,
    ):
        self.env = env
        self.output_queue = output_queue
        self.arrival_interval = arrival_interval
        self.arrival_std = arrival_std
        self.event_logger = event_logger
        self.rng = rng if rng is not None else np.random.default_rng()
        self.max_vehicles = max_vehicles

        self.dynamic_arrival_interval: Optional[Callable[[float], float]] = None
        self.vehicles_generated: int = 0
        self.active_vehicles: dict[str, VehicleState] = {}
        self._process = self.env.process(self._run())

    def _generate_vin(self, car_id_num: int) -> str:
        return f"1G1EV40A8R890{car_id_num:04d}"

    def get_effective_arrival_interval(self, t: Optional[float] = None) -> float:
        curr_t = self.env.now if t is None else t
        if self.dynamic_arrival_interval is not None:
            return float(self.dynamic_arrival_interval(curr_t))
        return float(self.arrival_interval)

    def _run(self):
        while True:
            if self.max_vehicles is not None and self.vehicles_generated >= self.max_vehicles:
                break

            car_num = 1000 + self.vehicles_generated + 1
            car_id = f"CAR-{car_num}"

            preset = self.rng.choice(MODEL_PRESETS)
            vehicle = VehicleState(
                id=car_id,
                model=preset["model"],
                color=preset["color"],
                color_name=preset["color_name"],
                vin=self._generate_vin(car_num),
                created_at=self.env.now,
            )

            self.active_vehicles[vehicle.id] = vehicle
            self.vehicles_generated += 1

            if self.event_logger:
                self.event_logger(
                    FactoryEvent(
                        timestamp=self.env.now,
                        event_type=EventType.VEHICLE_CREATED,
                        vehicle_id=vehicle.id,
                        details={
                            "model": vehicle.model.value,
                            "vin": vehicle.vin,
                            "color": vehicle.color_name,
                        },
                    )
                )

            yield self.output_queue.put(vehicle)

            base_interval = self.get_effective_arrival_interval()
            if self.arrival_std > 0:
                interval = float(max(1.0, self.rng.normal(base_interval, self.arrival_std)))
            else:
                interval = float(base_interval)

            yield self.env.timeout(interval)
