from pokersoft.cards import parse_cards
from pokersoft.decision import (
    Action,
    GameState,
    Street,
    analyze,
    minimum_defense_frequency,
    pot_odds,
)
from pokersoft.opponent_model import OpponentStats


def test_pot_odds_basic():
    assert pot_odds(10, 10) == 0.5
    assert pot_odds(0, 0) == 0.0
    assert round(pot_odds(9, 3), 4) == 0.25


def test_mdf_basic():
    assert minimum_defense_frequency(10, 10) == 0.5
    assert round(minimum_defense_frequency(6, 3), 4) == round(6 / 9, 4)


def test_premium_hand_always_opens_utg():
    state = GameState(
        hero_cards=parse_cards("Ah As"),
        street=Street.PREFLOP,
        position="UTG",
        stack_bb=100,
        pot_bb=1.5,
        to_call_bb=0,
        facing_preflop_raises=0,
    )
    result = analyze(state)
    assert result.gto.action == Action.RAISE


def test_trash_hand_folds_utg():
    state = GameState(
        hero_cards=parse_cards("7h 2c"),
        street=Street.PREFLOP,
        position="UTG",
        stack_bb=100,
        pot_bb=1.5,
        to_call_bb=0,
        facing_preflop_raises=0,
    )
    result = analyze(state)
    assert result.gto.action == Action.FOLD


def test_short_stack_shove_logic_engages():
    state = GameState(
        hero_cards=parse_cards("Ah Kd"),
        street=Street.PREFLOP,
        position="BTN",
        stack_bb=10,
        pot_bb=1.5,
        to_call_bb=0,
        facing_preflop_raises=0,
    )
    result = analyze(state)
    assert result.gto.action == Action.SHOVE
    assert result.gto.sizing_bb == 10


def test_nut_hand_river_recommends_call_or_raise_given_good_odds():
    state = GameState(
        hero_cards=parse_cards("Ah Kh"),
        board=parse_cards("2h 5h 9h Jd 3c"),
        street=Street.RIVER,
        pot_bb=10,
        to_call_bb=5,
        num_active_opponents=1,
    )
    result = analyze(state)
    assert result.gto.action in (Action.CALL, Action.RAISE)
    assert result.equity_result is not None
    assert result.equity_result.equity > 0.8


def test_exploit_matches_gto_without_enough_hands():
    stats = OpponentStats(name="villain", hands_observed=3, folded_to_cbet_count=3, faced_cbet_count=3)
    state = GameState(
        hero_cards=parse_cards("2h 2c"),
        board=parse_cards("9h 5d 3c"),
        street=Street.FLOP,
        pot_bb=6,
        to_call_bb=0,
        num_active_opponents=1,
        opponent_stats=stats,
    )
    result = analyze(state)
    assert result.exploit.action == result.gto.action


def test_exploit_deviates_with_reliable_high_fold_to_cbet():
    stats = OpponentStats(
        name="villain",
        hands_observed=40,
        folded_to_cbet_count=30,
        faced_cbet_count=40,
    )
    state = GameState(
        hero_cards=parse_cards("2h 2c"),
        board=parse_cards("9h 5d 3c"),
        street=Street.FLOP,
        pot_bb=6,
        to_call_bb=0,
        num_active_opponents=1,
        opponent_stats=stats,
    )
    result = analyze(state)
    if result.gto.action == Action.CHECK:
        assert result.exploit.action == Action.BET
