"""Shared helpers for experiment scripts."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

N_NODES = 100
N_TASKS = 10_000
MALICIOUS_FRACTION = 0.10
SEED = 42
