import pulp
from gbgolf.data.models import Card
from gbgolf.data.config import ContestConfig


def _solve_one_lineup(cards: list, config: ContestConfig) -> list | None:
    """Solve a single ILP lineup for the given card pool and contest config.

    Selects exactly config.roster_size cards from `cards` to maximize
    total effective_value subject to salary and collection constraints.

    Args:
        cards: list[Card] — available cards for this contest slot
        config: ContestConfig — salary bounds, roster size, collection limits

    Returns:
        list[Card] of selected cards if an optimal solution exists, or None
        if no feasible solution exists (infeasible/unbounded/unsolved).
        Never raises on infeasibility.
    """
    if not cards or len(cards) < config.roster_size:
        return None

    n = len(cards)
    prob = pulp.LpProblem("lineup", pulp.LpMaximize)

    # Binary variable per card: x[i] in {0, 1}
    x = [pulp.LpVariable(f"x_{i}", cat="Binary") for i in range(n)]

    # Objective: maximize total effective_value
    prob += pulp.lpSum((cards[i].effective_value or 0.0) * x[i] for i in range(n))

    # Roster size: exactly config.roster_size cards selected
    prob += pulp.lpSum(x[i] for i in range(n)) == config.roster_size

    # Salary floor
    prob += pulp.lpSum(cards[i].salary * x[i] for i in range(n)) >= config.salary_min

    # Salary cap
    prob += pulp.lpSum(cards[i].salary * x[i] for i in range(n)) <= config.salary_max

    # Collection limits (upper bounds only — never minimums)
    for collection_name, limit in config.collection_limits.items():
        eligible = [i for i, c in enumerate(cards) if c.collection == collection_name]
        if eligible:
            prob += pulp.lpSum(x[i] for i in eligible) <= limit

    # Same-player constraint: at most one card per player per lineup
    player_to_indices: dict[str, list[int]] = {}
    for i, c in enumerate(cards):
        player_to_indices.setdefault(c.player, []).append(i)
    for player, indices in player_to_indices.items():
        if len(indices) > 1:
            prob += pulp.lpSum(x[i] for i in indices) <= 1

    # Solve using CBC (msg=0 suppresses solver output)
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    # Return None for any non-optimal status
    if pulp.LpStatus[prob.status] != "Optimal":
        return None

    # Extract selected cards (use > 0.5 to handle CBC floating-point output)
    return [cards[i] for i in range(n) if x[i].varValue > 0.5]
