"""Compare a rerun's selected-match derived rows to the committed snapshot."""
import pandas as pd
from config import OUT, ROOT


def main():
    coverage = pd.read_csv(OUT / 'coverage.csv')
    usable = coverage[coverage.available]
    assert len(usable) > 0, 'No available replays'
    assert (usable.goal_events == usable.expected_goals).all()
    ids = set(usable.id)
    keys = {'robots': ['id','team','player'], 'teams': ['id','team'],
            'goals': ['id','kind','time'], 'goal_trajectories': ['id','event_id','seconds_before_goal'],
            'fouls_by_reason': ['id','team','reason'], 'coverage': ['id']}
    for name, sort in keys.items():
        actual = pd.read_csv(OUT / f'{name}.csv')
        expected = pd.read_csv(ROOT / f'{name}.csv')
        actual = actual[actual.id.isin(ids)].sort_values(sort).reset_index(drop=True)
        expected = expected[expected.id.isin(ids)].sort_values(sort).reset_index(drop=True)
        pd.testing.assert_frame_equal(actual, expected, check_dtype=False, check_exact=False, rtol=1e-9, atol=1e-9)
        print(f'REPRODUCED {name}.csv: {len(actual)} rows')
    for name in ['robots_OFFICIAL.png','robots_FREE_BATTLE.png','ball_heatmaps.png']:
        if (OUT / name).exists():
            assert (OUT / name).stat().st_size > 1000
    print(f'VERIFICATION OK: {len(ids)} replays; {int(usable.goal_events.sum())} goals reconciled; derived rows match committed outputs')


if __name__ == '__main__':
    main()
