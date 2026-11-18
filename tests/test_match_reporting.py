import unittest

from scripts.run_team_batch import summarize


class ReportingTest(unittest.TestCase):
    def setUp(self):
        self.result = {
            'status': 'finished', 'score': {'home': 3, 'away': 1},
            'winner': 'home', 'endReason': 'time_expired',
            'timing': {'regularDurationSeconds': 600},
            'durationSeconds': 800,
        }

    def test_score_is_relative_to_our_side(self):
        result = summarize(self.result, [], 'away', 'match-02')
        self.assertEqual((result['goals_for'], result['goals_against'], result['outcome']), (1, 3, 'loss'))
        self.assertEqual(result['score_home_away'], '3-1')

    def test_empty_event_list(self):
        result = summarize(self.result, [], 'home', 'match-01')
        self.assertEqual(result['our_fouls'], 0)
        self.assertEqual(result['our_fallen_penalties'], 0)
        self.assertEqual(result['warnings_total'], 0)

    def test_retake_warning_belongs_to_offender_not_beneficiary(self):
        events = [{'severity': 'warning', 'type': 'set_play_retake', 'actor': {'side': 'home'}, 'outcome': {'offendingActor': {'side': 'away'}}}]
        self.result['warnings'] = [{'type': 'set_play_retake'}]
        result = summarize(self.result, events, 'home', 'match-01')
        self.assertEqual(result['warnings_total'], 1)
        self.assertEqual(result['our_warning_events'], 0)
        self.assertEqual(summarize(self.result, events, 'away', 'match-02')['our_warning_events'], 1)

    def test_fallen_penalty_count_not_every_penalty(self):
        events = [
            {'type': 'penalty', 'actor': {'side': 'home'}, 'outcome': {'reason': 'fallenRobot'}},
            {'type': 'penalty', 'actor': {'side': 'home'}, 'outcome': {'reason': 'inactiveRobot'}},
        ]
        result = summarize(self.result, events, 'home', 'match-01')
        self.assertEqual(result['our_fouls'], 2)
        self.assertEqual(result['our_fallen_penalties'], 1)

    def test_retake_without_named_offender_belongs_to_defending_side(self):
        events = [{'severity': 'warning', 'type': 'set_play_retake', 'actor': {'side': 'home'}, 'outcome': {'reason': 'free_kick_avoidance_radius', 'offendingActor': None}}]
        self.assertEqual(summarize(self.result, events, 'home', 'match-01')['our_warning_events'], 0)
        self.assertEqual(summarize(self.result, events, 'away', 'match-02')['our_warning_events'], 1)

    def test_invalid_result_rejected(self):
        with self.assertRaises(KeyError):
            summarize({'status': 'running', 'result': None}, [], 'home', 'bad')


if __name__ == '__main__':
    unittest.main()
