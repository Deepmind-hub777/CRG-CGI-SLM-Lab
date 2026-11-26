#!/usr/bin/env python3
"""Synthetic smoke test for the ternary sampler.

This does NOT load a model. It checks the math in SPEC/01 on a toy
distribution, so that a broken sampler is caught before it touches a
real model.

Run:
    python3 lab/00-smoke-test/test_sampler.py

Exit code 0 = all checks pass.
"""

from __future__ import annotations

import hashlib
import math
from typing import Iterable, List


VOCAB = ["A", "B", "C", "D", "E", "F"]

# Toy logits: baseline is fairly flat; anchor prefers tokens 0 and 1.
BASE = [2.0, 1.2, 0.8, 0.1, -0.5, -1.0]
ANCHOR = [3.0, 2.6, 1.0, -1.0, -2.0, -3.0]
ANCHOR_IDS = [0, 1]


def softmax(logits: Iterable[float], temperature: float = 1.0) -> List[float]:
    if temperature <= 0:
        raise ValueError("temperature must be > 0")
    values = list(logits)
    maximum = max(values)
    exps = [math.exp((v - maximum) / temperature) for v in values]
    total = sum(exps)
    return [e / total for e in exps]


def entropy(probs: Iterable[float]) -> float:
    return -sum(p * math.log(p) for p in probs if p > 0.0)


def kl_divergence(p: Iterable[float], q: Iterable[float]) -> float:
    return sum(pi * math.log(pi / qi) for pi, qi in zip(p, q) if pi > 0.0)


def ternary_logits(
    base: Iterable[float],
    anchor: Iterable[float],
    beta: float,
    gamma: float,
    temperature: float = 1.0,
) -> List[float]:
    """SPEC/01: l = f + beta*a - gamma*d, d_i = max(0, p_i - q_i)."""
    base = list(base)
    anchor = list(anchor)
    if len(base) != len(anchor):
        raise ValueError("base and anchor must have the same vocabulary size")

    p = softmax(base, temperature)
    q = softmax(anchor, temperature)
    divergence = [max(0.0, pi - qi) for pi, qi in zip(p, q)]

    return [
        b + beta * a - gamma * d
        for b, a, d in zip(base, anchor, divergence)
    ]


def mass(probs: Iterable[float], ids: Iterable[int]) -> float:
    values = list(probs)
    return sum(values[i] for i in ids)


def top_k_ids(probs: Iterable[float], k: int = 3) -> List[int]:
    values = list(probs)
    return sorted(range(len(values)), key=lambda i: (-values[i], i))[:k]


def top_k_hash(probs: Iterable[float], k: int = 3) -> str:
    values = list(probs)
    order = top_k_ids(values, k)
    payload = "|".join(f"{VOCAB[i]}:{values[i]:.8f}" for i in order)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def approx_equal(a: Iterable[float], b: Iterable[float], tol: float = 1e-12) -> bool:
    return max(abs(x - y) for x, y in zip(a, b)) <= tol


def main() -> int:
    base_p = softmax(BASE)
    anchor_p = softmax(ANCHOR)
    print("Toy vocabulary:", ", ".join(VOCAB))
    print(f"baseline entropy = {entropy(base_p):.4f}")
    print(f"anchor entropy   = {entropy(anchor_p):.4f}")
    print(f"baseline anchor mass = {mass(base_p, ANCHOR_IDS):.4f}")
    print()

    # 1. beta=0, gamma=0 must be a no-op.
    zero_p = softmax(ternary_logits(BASE, ANCHOR, beta=0.0, gamma=0.0))
    assert approx_equal(base_p, zero_p), "beta=0,gamma=0 changed the distribution"
    print("[PASS] zero-order baseline is a no-op")

    # 2. Anchor pull: beta > 0 must increase mass on anchor ids.
    beta = 0.8
    anchored_p = softmax(ternary_logits(BASE, ANCHOR, beta=beta, gamma=0.0))
    anchored_mass = mass(anchored_p, ANCHOR_IDS)
    assert anchored_mass > mass(base_p, ANCHOR_IDS) + 0.10, (
        f"anchor pull too weak: {mass(base_p, ANCHOR_IDS):.4f} -> {anchored_mass:.4f}"
    )
    print(
        f"[PASS] anchor pull: mass {mass(base_p, ANCHOR_IDS):.4f} -> {anchored_mass:.4f}"
    )

    # 3. No collapse: entropy stays above a floor.
    floor = 0.60
    assert entropy(anchored_p) >= floor, (
        f"entropy collapsed: {entropy(anchored_p):.4f} < {floor}"
    )
    print(f"[PASS] entropy floor: {entropy(anchored_p):.4f} >= {floor}")

    # 4. Divergence penalty: gamma > 0 must reduce off-anchor mass.
    gamma = 2.0
    penalized_p = softmax(ternary_logits(BASE, ANCHOR, beta=beta, gamma=gamma))
    off_before = 1.0 - anchored_mass
    off_after = 1.0 - mass(penalized_p, ANCHOR_IDS)
    assert off_after < off_before, (
        f"divergence penalty did not reduce off-anchor mass: "
        f"{off_before:.4f} -> {off_after:.4f}"
    )
    print(
        f"[PASS] divergence penalty: off-anchor mass {off_before:.4f} -> {off_after:.4f}"
    )

    # 5. Self-anchor does not create a new origin. If the "anchor" is the
    #    model itself, adding beta*a only sharpens the existing distribution;
    #    it cannot pull toward a different direction. This is a guard against
    #    fake anchoring: a model cannot supply its own origin.
    self_p = softmax(ternary_logits(BASE, BASE, beta=beta, gamma=0.0))
    assert top_k_ids(self_p) == top_k_ids(base_p), (
        "self-anchor changed the top-k order; that should not happen"
    )
    assert entropy(self_p) <= entropy(base_p), (
        "self-anchor increased entropy; check the sampler"
    )
    print(
        "[PASS] self-anchor only sharpens; it cannot create a new origin "
        f"(H {entropy(base_p):.4f} -> {entropy(self_p):.4f})"
    )

    # 6. Reproducibility fingerprint.
    fingerprint = top_k_hash(penalized_p)
    print(f"[PASS] top_k_hash = {fingerprint}")

    print()
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
