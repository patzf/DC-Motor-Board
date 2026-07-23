from dataclasses import dataclass


@dataclass(slots=True)
class MeasurementSample:
    timestamp: float
    voltage: float
    current: float
