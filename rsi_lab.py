"""CPU experiments for the RSI course. All weights are counts for four candidate rules."""
import random

NAMES = ["前进一步", "前进两格", "前进三格", "后退一步"]
MOVES = (1, 2, 3, -1)
INITIAL = [[5, 2, 1, 1], [1, 4, 2, 2], [4, 2, 1, 2], [2, 4, 2, 1]]
TRAIN, DEV, TEST = range(50), range(50, 75), range(75, 100)


def answer(x, rule):
    return (x + MOVES[rule]) % 10


def verified(x, instruction, prediction):
    return prediction == (x + (1, 2, 3, -1)[instruction]) % 10


def evaluate(weights, inputs):
    groups = []
    greedy_hits = 0
    for task, row in enumerate(weights):
        best = row.index(max(row))
        total = 0
        for x in inputs:
            greedy_hits += verified(x, task, answer(x, best))
            total += sum(w for rule, w in enumerate(row)
                         if verified(x, task, answer(x, rule)))
        groups.append(total / (len(inputs) * sum(row)))
    return dict(expected=sum(groups) / len(groups), by_task=groups,
                greedy=greedy_hits / (len(inputs) * len(weights)))


def sample_batch(rng, weights, mix, budget):
    batch = []
    for _ in range(budget):
        task = rng.choices(range(len(NAMES)), weights=mix)[0]
        x = rng.choice(TRAIN)
        rule = rng.choices(range(len(MOVES)), weights=weights[task])[0]
        batch.append((task, x, rule, answer(x, rule)))
    return batch


def update(weights, batch, verifier=verified):
    next_weights = [row.copy() for row in weights]
    attempts = [0] * len(NAMES)
    kept = [0] * len(NAMES)
    for task, x, rule, prediction in batch:
        attempts[task] += 1
        if verifier(x, task, prediction):
            kept[task] += 1
            next_weights[task][rule] += 1
    return next_weights, attempts, kept


def next_mix(attempts, kept):
    return [(a - k + 1) / (a + 2) for a, k in zip(attempts, kept)]


def train(seed, adaptive, budget=32, rounds=5, initial=INITIAL, verifier=verified):
    rng = random.Random(seed)
    weights = [row.copy() for row in initial]
    mix = [1.0] * len(NAMES)
    history = []
    for epoch in range(1, rounds + 1):
        batch = sample_batch(rng, weights, mix, budget)
        weights, attempts, kept = update(weights, batch, verifier)
        history.append(dict(epoch=epoch, attempts=attempts, kept=kept,
                            dev=evaluate(weights, DEV)))
        if adaptive:
            mix = next_mix(attempts, kept)
    return weights, history
