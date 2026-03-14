import pulp
from gbgolf.data.models import Card
from gbgolf.data.config import ContestConfig


def _solve_one_lineup(cards: list, config: ContestConfig) -> list | None:
    """Solve a single ILP lineup for the given card pool and contest config.

    Args:
        cards: list[Card] — available cards for this contest slot
        config: ContestConfig — salary bounds, roster size, collection limits

    Returns:
        list[Card] of selected cards, or None if infeasible
    """
    raise NotImplementedError("_solve_one_lineup() not yet implemented")
