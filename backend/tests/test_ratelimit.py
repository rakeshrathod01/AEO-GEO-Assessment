from app.services.ratelimit import RateLimiter


def test_no_throttle_when_rate_zero():
    rl = RateLimiter()
    waits = []
    for _ in range(5):
        waits.append(rl.acquire("p", 0, sleep=lambda w: None))
    assert waits == [0.0] * 5


def test_enforces_min_interval():
    rl = RateLimiter()
    recorded = []
    # rate 10/sec -> 0.1s spacing. Use a fake sleep so the test stays fast.
    for _ in range(4):
        rl.acquire("ahrefs", 10, sleep=lambda w: recorded.append(w))
    # First call fires immediately (no sleep); the next three each wait ~0.1s.
    assert len(recorded) == 3
    assert all(w > 0.05 for w in recorded)


def test_keys_are_independent():
    rl = RateLimiter()
    w_a = rl.acquire("a", 1, sleep=lambda w: None)
    w_b = rl.acquire("b", 1, sleep=lambda w: None)
    assert w_a == 0.0 and w_b == 0.0  # different keys don't block each other
