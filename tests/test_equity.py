from pokersoft.cards import parse_cards
from pokersoft.equity import hand_equity


def test_aa_dominates_random_opponent_heads_up():
    hero = parse_cards("Ah As")
    result = hand_equity(hero, [], num_random_opponents=1, trials=3000, seed=42)
    # AA vs random hand heads-up is a well known ~85% equity benchmark
    assert 0.78 <= result.equity <= 0.90


def test_kk_vs_aa_preflop_is_a_big_dog():
    hero = parse_cards("Kh Ks")
    from pokersoft.ranges import parse_range

    villain_range = parse_range("AA")
    result = hand_equity(hero, [], opponent_ranges=[villain_range], trials=3000, seed=7)
    assert 0.12 <= result.equity <= 0.22


def test_nut_flush_on_river_is_near_certain():
    hero = parse_cards("Ah Kh")
    board = parse_cards("2h 5h 9h Jd 3c")
    result = hand_equity(hero, board, num_random_opponents=1, trials=2000, seed=1)
    assert result.equity >= 0.85
