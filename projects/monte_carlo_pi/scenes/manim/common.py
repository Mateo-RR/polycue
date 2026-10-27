"""Random dots shared by the monte_carlo_pi scenes, so every scene shows the same sample."""

import numpy as np

SEED = 163  # picked so the sample lands close to π (1178 of 1500 inside → 3.1413)
N_DOTS = 1500  # dots dropped in scene 2 and counted in scene 3
N_RUN = 20000  # dots behind the running estimate of scene 4 (the first N_DOTS are the same)


def points(n: int) -> np.ndarray:
    """n points uniform in the square [-1, 1]², always the same for a given n prefix."""
    return np.random.default_rng(SEED).uniform(-1, 1, size=(n, 2))


def inside(pts: np.ndarray) -> np.ndarray:
    """True for the points inside the unit circle."""
    return (pts ** 2).sum(axis=1) <= 1


def running_estimate(n: int) -> np.ndarray:
    """4 · inside / total after each of the first n dots."""
    hits = np.cumsum(inside(points(n)))
    return 4 * hits / np.arange(1, n + 1)
