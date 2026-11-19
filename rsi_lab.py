"""RSI 课程共用的算术实验：按策略采样、校验答案，再用通过的样本更新权重。"""
import random

NAMES = ["前进一步", "前进两格", "前进三格", "后退一步"]
MOVES = (1, 2, 3, -1)
# 行表示题目指令，列表示候选规则。例如第一行抽中正确规则的概率是 5/9。
INITIAL = [[5, 2, 1, 1], [1, 4, 2, 2], [4, 2, 1, 2], [2, 4, 2, 1]]
TRAIN, DEV, TEST = range(50), range(50, 75), range(75, 100)


def answer(x, rule):
    return (x + MOVES[rule]) % 10


def verified(x, instruction, prediction):
    return prediction == (x + (1, 2, 3, -1)[instruction]) % 10


def evaluate(weights, inputs):
    """在同一批起点上，分别评估按权重采样和总选最高权重规则的正确率。"""
    groups = []
    greedy_hits = 0
    for task, row in enumerate(weights):
        # 并列时总选第一条规则，保证贪心分数可复现。
        best = row.index(max(row))
        total = 0
        for x in inputs:
            greedy_hits += verified(x, task, answer(x, best))
            # 累加能答对的规则权重，最后除以总权重即可得到精确概率。
            total += sum(w for rule, w in enumerate(row)
                         if verified(x, task, answer(x, rule)))
        groups.append(total / (len(inputs) * sum(row)))
    return dict(expected=sum(groups) / len(groups), by_task=groups,
                greedy=greedy_hits / (len(inputs) * len(weights)))


def sample_batch(rng, weights, mix, budget):
    """mix 决定抽哪类题，weights[task] 决定用哪条规则解这道题。"""
    batch = []
    for _ in range(budget):
        task = rng.choices(range(len(NAMES)), weights=mix)[0]
        x = rng.choice(TRAIN)
        rule = rng.choices(range(len(MOVES)), weights=weights[task])[0]
        batch.append((task, x, rule, answer(x, rule)))
    return batch


def update(weights, batch, verifier=verified):
    # 逐行复制，保留更新前的策略，方便第四课直接对照两张权重表。
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
    # 平滑后，没抽到的题型权重为 1/2；调用 choices 时会按总和归一化。
    return [(a - k + 1) / (a + 2) for a, k in zip(attempts, kept)]


def train(seed, adaptive, budget=32, rounds=5, initial=INITIAL, verifier=verified):
    """每轮先采满 budget 个样本，再统一更新；adaptive 控制下一轮的出题比例。"""
    rng = random.Random(seed)
    weights = [row.copy() for row in initial]
    mix = [1.0] * len(NAMES)
    history = []
    for epoch in range(1, rounds + 1):
        batch = sample_batch(rng, weights, mix, budget)
        weights, attempts, kept = update(weights, batch, verifier)
        # 第六课会替换训练校验器；开发集始终用精确答案衡量实际表现。
        history.append(dict(epoch=epoch, attempts=attempts, kept=kept,
                            dev=evaluate(weights, DEV)))
        if adaptive:
            mix = next_mix(attempts, kept)
    return weights, history
