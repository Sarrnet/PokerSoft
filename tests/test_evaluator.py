from pokersoft.cards import parse_cards
from pokersoft.evaluator import evaluate_5, evaluate_best, describe


def score(text):
    return evaluate_5(parse_cards(text))


def test_category_ordering():
    straight_flush = score("9h 8h 7h 6h 5h")
    quads = score("2h 2s 2d 2c 9h")
    full_house = score("3h 3s 3d 9h 9s")
    flush = score("2h 5h 9h Jh Kh")
    straight = score("4h 5s 6d 7c 8h")
    trips = score("5h 5s 5d 9c 2h")
    two_pair = score("5h 5s 9d 9c 2h")
    one_pair = score("5h 5s 9d Kc 2h")
    high_card = score("2h 5s 9d Kc Jh")

    ordered = [
        high_card, one_pair, two_pair, trips, straight, flush, full_house, quads, straight_flush,
    ]
    for lower, higher in zip(ordered, ordered[1:]):
        assert lower < higher, (lower, higher)

    assert describe(straight_flush) == "стрит-флеш"
    assert describe(quads) == "каре"


def test_wheel_straight():
    wheel = score("Ah 2s 3d 4c 5h")
    six_high = score("2h 3s 4d 5c 6h")
    assert wheel[0] == 4
    assert wheel[1] == (5,)
    assert wheel < six_high


def test_kicker_breaks_tie_for_pairs():
    pair_ace_kicker = score("5h 5s 9d Ac 2h")
    pair_king_kicker = score("5h 5s 9d Kc 2h")
    assert pair_ace_kicker > pair_king_kicker


def test_evaluate_best_picks_top_5_of_7():
    seven = parse_cards("Ah Kh Qh Jh Th 2c 3d")
    best = evaluate_best(seven)
    assert best[0] == 8  # royal-ish straight flush
    assert best[1] == (14,)


def test_flush_beats_straight():
    f = score("2h 5h 9h Jh Kh")
    s = score("4h 5s 6d 7c 8h")
    assert f > s
