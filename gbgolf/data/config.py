import json
from dataclasses import dataclass
from typing import Any
from pydantic import BaseModel, model_validator


@dataclass
class ContestConfig:
    """Plain dataclass — internal representation of one contest's parameters."""
    name: str
    salary_min: int
    salary_max: int
    roster_size: int
    max_entries: int
    collection_limits: dict[str, int]


class _ContestConfigModel(BaseModel):
    """Pydantic validation model — used only at the config file boundary."""
    name: str
    salary_min: int
    salary_max: int
    roster_size: int
    max_entries: int
    collection_limits: dict[str, int]

    @model_validator(mode="after")
    def salary_range_valid(self) -> "_ContestConfigModel":
        if self.salary_max <= self.salary_min:
            raise ValueError(
                f"salary_max ({self.salary_max}) must be greater than "
                f"salary_min ({self.salary_min}) for contest '{self.name}'"
            )
        return self


class _ConfigFile(BaseModel):
    contests: list[_ContestConfigModel]


def load_contest_config(path: str) -> list[ContestConfig]:
    """
    Load and validate contest_config.json.
    Returns a list of ContestConfig dataclasses.
    Raises pydantic.ValidationError if the file is malformed.
    Raises FileNotFoundError if path does not exist.
    """
    with open(path, encoding="utf-8") as f:
        raw: Any = json.load(f)
    config_file = _ConfigFile.model_validate(raw)
    return [
        ContestConfig(
            name=m.name,
            salary_min=m.salary_min,
            salary_max=m.salary_max,
            roster_size=m.roster_size,
            max_entries=m.max_entries,
            collection_limits=m.collection_limits,
        )
        for m in config_file.contests
    ]
