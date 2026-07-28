from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlanetaryAge:
    planet_name: str
    age_years: int
