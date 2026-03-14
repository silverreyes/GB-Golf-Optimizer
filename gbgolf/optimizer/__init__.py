from dataclasses import dataclass, field
from gbgolf.data.models import Card


@dataclass
class Lineup:
    """Represents a single optimized lineup for a contest."""
    contest: str
    cards: list  # list[Card]

    def __post_init__(self):
        self.total_salary: int = sum(c.salary for c in self.cards)
        self.total_projected_score: float = sum(
            (c.projected_score or 0.0) for c in self.cards
        )
        self.total_effective_value: float = sum(
            (c.effective_value or 0.0) for c in self.cards
        )


@dataclass
class OptimizationResult:
    """Result of running the optimizer across all contests."""
    lineups: dict  # dict[str, list[Lineup]]
    unused_cards: list  # list[Card]
    infeasibility_notices: list  # list[str]


def optimize(valid_cards: list, contests: list) -> OptimizationResult:
    """Generate optimal lineups for each contest.

    Args:
        valid_cards: list[Card] from the validation pipeline
        contests: list[ContestConfig] defining each contest's constraints

    Returns:
        OptimizationResult with lineups per contest and any infeasibility notices
    """
    raise NotImplementedError("optimize() not yet implemented")


__all__ = ["optimize", "OptimizationResult", "Lineup"]
