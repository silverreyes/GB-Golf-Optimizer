from dataclasses import dataclass, field
from gbgolf.data.models import Card
from gbgolf.optimizer.engine import _solve_one_lineup


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

    For each contest, generates up to max_entries lineups by iteratively
    calling _solve_one_lineup. Cards used in previous lineups are excluded
    from the pool for subsequent lineups (disjoint card usage).

    Args:
        valid_cards: list[Card] from the validation pipeline
        contests: list[ContestConfig] defining each contest's constraints

    Returns:
        OptimizationResult with lineups per contest and any infeasibility notices
    """
    lineups: dict = {}
    infeasibility_notices: list = []
    used_card_ids: set = set()

    for config in contests:
        contest_lineups: list = []

        for entry_num in range(config.max_entries):
            # Exclude cards already used in previous lineups (disjoint pool)
            available = [c for c in valid_cards if id(c) not in used_card_ids]

            result = _solve_one_lineup(available, config)

            if result is None:
                notice = (
                    f"{config.name}: lineup {entry_num + 1} of {config.max_entries} "
                    f"could not be built (infeasible)"
                )
                infeasibility_notices.append(notice)
            else:
                # Mark these cards as used
                for card in result:
                    used_card_ids.add(id(card))
                contest_lineups.append(Lineup(contest=config.name, cards=result))

        lineups[config.name] = contest_lineups

    unused_cards = [c for c in valid_cards if id(c) not in used_card_ids]

    return OptimizationResult(
        lineups=lineups,
        unused_cards=unused_cards,
        infeasibility_notices=infeasibility_notices,
    )


__all__ = ["optimize", "OptimizationResult", "Lineup"]
