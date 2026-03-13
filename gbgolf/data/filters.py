from datetime import date
from gbgolf.data.models import Card, ExclusionRecord


def apply_filters(cards: list[Card]) -> tuple[list[Card], list[ExclusionRecord]]:
    """
    Apply all three exclusion rules to a card list.
    Returns (valid_cards, excluded).

    Exclusion rules (first match wins):
      1. $0 salary — player not in tournament field
      2. Expired card — expires < today (card expiring today is still valid)
      3. No projection found — projected_score is None
    """
    today = date.today()
    valid: list[Card] = []
    excluded: list[ExclusionRecord] = []

    for card in cards:
        if card.salary == 0:
            excluded.append(ExclusionRecord(player=card.player, reason="$0 salary"))
        elif card.expires is not None and card.expires < today:
            excluded.append(ExclusionRecord(player=card.player, reason="expired card"))
        elif card.projected_score is None:
            excluded.append(ExclusionRecord(player=card.player, reason="no projection found"))
        else:
            valid.append(card)

    return valid, excluded
