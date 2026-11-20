"""Short-window ball motion estimates for roamer movement only."""
import math

from .field_params import (
    BALL_PRED_WINDOW_S, BALL_PRED_GAP_S, BALL_PRED_MAX_SPEED_MPS,
    BALL_PRED_SLOW_MPS, BALL_PRED_HORIZON_S, BALL_PRED_FRICTION,
    BALL_PRED_WALK_MPS, BALL_PRED_MARGIN_M,
)


class BallPredictor:
    def __init__(self):
        self.samples = []
        self.velocity = (0.0, 0.0)

    def reset(self):
        self.samples.clear()
        self.velocity = (0.0, 0.0)

    def observe(self, ball, now, enabled=True):
        if (not enabled or ball is None
                or not all(math.isfinite(v) for v in (ball.x, ball.y, ball.last_seen_at, now))
                or now - ball.last_seen_at > BALL_PRED_GAP_S
                or ball.last_seen_at > now):
            self.reset()
            return
        t, x, y = ball.last_seen_at, ball.x, ball.y
        if self.samples:
            pt, px, py = self.samples[-1]
            dt = t - pt
            if dt == 0 and (x, y) == (px, py):
                return
            if (dt <= 0 or dt > BALL_PRED_GAP_S
                    or math.hypot(x - px, y - py) > BALL_PRED_MAX_SPEED_MPS * dt):
                self.reset()
        self.samples.append((t, x, y))
        self.samples = [s for s in self.samples if t - s[0] <= BALL_PRED_WINDOW_S]
        mean_t = sum(s[0] - t for s in self.samples) / len(self.samples)
        variance = sum((s[0] - t - mean_t) ** 2 for s in self.samples)
        self.velocity = tuple(
            sum((s[0] - t - mean_t) * (s[axis] - self.samples[-1][axis])
                for s in self.samples) / variance if variance > 1e-8 else 0.0
            for axis in (1, 2)
        )
        if math.hypot(*self.velocity) < BALL_PRED_SLOW_MPS:
            self.velocity = (0.0, 0.0)

    def target(self, ball, pose, field):
        if self.velocity == (0.0, 0.0) or pose is None:
            return (ball.x, ball.y)
        horizon = min(BALL_PRED_HORIZON_S,
                      math.hypot(ball.x - pose.x, ball.y - pose.y) / BALL_PRED_WALK_MPS)
        # Two bounded arrival-time refinements, with exponential rolling decay.
        for _ in range(2):
            travel = -math.expm1(-BALL_PRED_FRICTION * horizon) / BALL_PRED_FRICTION
            x, y = ball.x + self.velocity[0] * travel, ball.y + self.velocity[1] * travel
            x = max(-field.length / 2 + BALL_PRED_MARGIN_M,
                    min(field.length / 2 - BALL_PRED_MARGIN_M, x))
            y = max(-field.width / 2 + BALL_PRED_MARGIN_M,
                    min(field.width / 2 - BALL_PRED_MARGIN_M, y))
            horizon = min(BALL_PRED_HORIZON_S, math.hypot(x - pose.x, y - pose.y) / BALL_PRED_WALK_MPS)
        return (x, y)
