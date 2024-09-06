from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime

from .types import LabelsDict


@dataclass
class ArrayDescription:
    name: str
    shape: tuple[int, ...] | None = None
    min_max: tuple[float, float] | None = None

    @property
    def __str__(self):
        if self.shape:
            return f"{self.name}{self.shape}"
        return self.name


@dataclass
class DatasetDescription:
    """Descriptive information about a dataset"""
    uid: str
    """Unique id of dataset"""
    name: str
    """Name of dataset"""
    collected_datetime: datetime
    """Time data was collected"""
    rating: int = 0
    """Rating: 0 = default; -1 = hidden; +1 = favorite"""
    labels: LabelsDict = field(default_factory=dict)
    """Labels attached to the dataset"""

    description: str | None = None
    variables: list[ArrayDescription] | None = None
    coordinates: list[ArrayDescription] | None = None

    @property
    def collected_date(self) -> date:
        return self.collected_datetime.date()

    @property
    def variables_text(self) -> str:
        if not self.variables:
            return ""
        return ', '.join(str(var) for var in self.variables)

    @property
    def coordinates_text(self) -> str:
        if not self.coordinates:
            return ""
        return ', '.join(str(coord) for coord in self.coordinates)

    def get_text(self, attr) -> str:
        if attr in ["uid", "name", "description"]:
            return getattr(self, attr)
        if attr == "rating":
            return f"{self.rating:+d}" if self.rating else ""
        if attr == "time":
            return f"{self.collected_datetime:%H:%M:%S}"
        if attr == "date":
            return f"{self.collected_datetime:%Y-%m-%d}"
        if attr == "variables":
            return self.variables_text
        if attr == "coordinates":
            return self.coordinates_text
        if attr in self.labels:
            value = self.labels[attr]
            if isinstance(value, str):
                return value
            if isinstance(value, Sequence):
                return ', '.join(value)
            return str(value)
        return "??"

