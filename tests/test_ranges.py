from pokersoft.cards import Card
from pokersoft.ranges import all_169_hands, parse_range


def test_all_169_hands_count():
    assert len(all_169_hands()) == 169


def test_parse_pair_plus():
    r = parse_range("QQ+")
    # QQ, KK, AA => 3 pairs * 6 combos = 18
    assert len(r) == 18
    assert all(w == 1.0 for w in r.values())


def test_parse_suited_plus_top_card_fixed():
    r = parse_range("ATs+")
    # ATs, AJs, AQs, AKs -> 4 hands * 4 combos = 16
    assert len(r) == 16
    for combo in r:
        ranks = sorted(c.rank for c in combo)
        assert ranks[1] == 14  # ace high
        suits = {c.suit for c in combo}
        assert len(suits) == 1  # suited


def test_parse_weight():
    r = parse_range("AJo:0.5")
    assert len(r) == 12  # AJ offsuit combos
    assert all(w == 0.5 for w in r.values())


def test_parse_both_suited_and_offsuit():
    r = parse_range("AK")
    assert len(r) == 16  # 4 suited + 12 offsuit
