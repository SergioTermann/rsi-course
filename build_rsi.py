"""Build the editable notebook for the RSI course."""
import json
from pathlib import Path

cells = []


def add(kind, source):
    cell = dict(cell_type=kind, id=f"rsi-{len(cells):02}", metadata={},
                source=source.strip().splitlines(keepends=True))
    if kind == "code":
        cell.update(execution_count=None, outputs=[])
    cells.append(cell)


add("markdown", """
# 递归自我改进（RSI）实验课

本课从一个训练问题出发：当本轮得到的策略可以决定下一轮怎样练习时，怎样判断它真的学得更好了？

你会搭建一个能出答案、筛样本、调整练习分配的小系统，并比较冻结策略、一次更新和多轮更新。只需 Python 标准库和 Jupyter，CPU 即可。建议用 25 分钟逐格运行，再改一个参数复做实验。

## 1 · 给「改进」一个可检验的定义

一道题由起点 x 和指令组成，答案是移动后的个位数字。例如起点 8、指令「前进三格」，答案是 1。策略从四条候选移动规则中抽取一条。每条指令各有一组权重，权重越大，对应规则越容易被抽到。初始策略对后两种指令有错误偏好。

每轮从当前策略采样，只保留通过算术校验的回答，用它们增加对应规则的权重。再根据本轮失败次数，更新下轮的出题分布。这里有两条反馈路径：答对的样本改变解题策略，暴露的弱项改变下一轮训练数据的分配。这个有限模型演示了递归反馈中的一个机制；校验器、更新公式和候选规则都由人给定，实验结论限于这个任务。
""")
add("code", """
import json
import random
from pathlib import Path

NAMES = ["前进一步", "前进两格", "前进三格", "后退一步"]
MOVES = [1, 2, 3, -1]
INITIAL = [[5, 2, 1, 1], [1, 4, 2, 2], [4, 2, 1, 2], [2, 4, 2, 1]]
TRAIN, DEV, TEST = range(50), range(50, 75), range(75, 100)
SEED, BUDGET, ROUNDS = 19, 32, 5
assert set(TRAIN).isdisjoint(DEV) and set(TEST).isdisjoint(set(TRAIN) | set(DEV))


def answer(x, rule):
    return (x + MOVES[rule]) % 10


def verified(x, instruction, prediction):
    return prediction == (x + (1, 2, 3, -1)[instruction]) % 10


assert verified(8, 2, 1) and not verified(8, 2, 9)
""")
add("markdown", """
## 2 · 先测量，再更新

独立评估枚举每条指令和留出起点。记录两个指标：按权重采样时的**期望正确率**，以及每次都选最大权重规则时的**贪心正确率**（并列时取第一条）。先猜一猜：某条正确规则的权重增加了，哪个指标可能完全不动？

这些规则对所有起点共享同一偏移，所以换起点只能检查同类任务上的表现。开发集与最终集都按指令等权，理论分数会相同；这个设计无法检验对新指令的泛化。
""")
add("code", """
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


print(evaluate(INITIAL, DEV))
""")
add("markdown", """
## 3 · 让本轮策略训练下一轮

先冻结本轮权重采完整批，再一次性更新。每条通过校验的轨迹给所选规则加 1；没有合格样本的指令保留原权重。自适应模式用各指令的平滑失败率 (失败数 + 1)/(尝试数 + 2) 分配下一轮预算，仍给每组保留采样机会。均匀模式只关闭这条出题反馈，两种模式都更新解题权重。

每轮先看尝试数和通过数，再看正确率。通过数还受出题分布影响，跨轮比较应使用固定的开发题。
""")
add("code", """
def train(seed, adaptive, budget=BUDGET, rounds=ROUNDS):
    rng = random.Random(seed)
    weights = [row.copy() for row in INITIAL]
    mix = [1.0] * len(NAMES)
    history = []
    for epoch in range(1, rounds + 1):
        attempts = [0] * len(NAMES)
        kept = [0] * len(NAMES)
        next_weights = [row.copy() for row in weights]
        for _ in range(budget):
            task = rng.choices(range(len(NAMES)), weights=mix)[0]
            x = rng.choice(TRAIN)
            rule = rng.choices(range(len(MOVES)), weights=weights[task])[0]
            attempts[task] += 1
            if verified(x, task, answer(x, rule)):
                next_weights[task][rule] += 1
                kept[task] += 1
        weights = next_weights
        history.append(dict(epoch=epoch, attempts=attempts, kept=kept,
                            dev=evaluate(weights, DEV)))
        if adaptive:
            mix = [(a - k + 1) / (a + 2) for a, k in zip(attempts, kept)]
    return weights, history


weights, history = train(SEED, adaptive=True)
for row in history:
    print(row["epoch"], row["attempts"], row["kept"],
          [round(score, 2) for score in row["dev"]["by_task"]])
""")
add("markdown", """
## 4 · 拆开预算与反馈的作用

冻结组给出起点。一轮组一次花完全部采样预算，多轮均匀组把相同预算拆成多批，让上一轮的新策略参与下一次采样。最后只打开按失败率调整出题的开关。先在开发集观察，再运行下格，在固定的种子列表和最终题集上报告全部结果。不要挑得分最高的种子。

请比较同一种子下各组的差值，并观察最弱指令。哪一组对照能回答「中途更新解题策略有用吗」？哪一组能回答「调整下一轮出题有用吗」？
""")
add("code", """
results = []
for seed in (SEED, SEED + 1, SEED + 2):
    for name, adaptive, budget, rounds in [
        ("冻结", False, 0, 0),
        ("一轮", False, BUDGET * ROUNDS, 1),
        ("多轮均匀", False, BUDGET, ROUNDS),
        ("多轮自适应", True, BUDGET, ROUNDS),
    ]:
        model, trace = train(seed, adaptive, budget, rounds)
        score = evaluate(model, TEST)
        draws = sum(sum(row["attempts"]) for row in trace)
        assert draws == budget * rounds
        # 精确校验器只接受正确规则，分组期望正确率应单调不降。
        previous = evaluate(INITIAL, DEV)["by_task"]
        for row in trace:
            current = row["dev"]["by_task"]
            assert all(a >= b for a, b in zip(current, previous))
            previous = current
        results.append(dict(seed=seed, mode=name, draws=draws, score=score))
        print(seed, name, draws, "期望 %.1f%%  贪心 %.1f%%  最弱组 %.1f%%" %
              (100 * score["expected"], 100 * score["greedy"], 100 * min(score["by_task"])))
""")
add("markdown", """
## 5 · 保存证据与验收

1. 从逐轮记录中挑出一条最难的指令，写下它首轮与末轮的尝试数、通过数、期望正确率。若某轮无人答对，解释下一轮还能通过什么途径得到第一个正样本。
2. 用同一种子的三种训练结果，分别计算多轮均匀减去一轮、多轮自适应减去多轮均匀的差值。看到贪心分数相同而期望分数不同，回到第二节解释原因。
3. 把某条指令的正确规则初始权重设为 0，其他权重保持为正。先预测它在多轮自适应组的末轮得分，再从头运行。增加出题次数能否补回策略永远采不到的答案？
4. 回到真实 verl 任务：若校验器只检查格式，哪些错误答案会被保留？写出一条能通过格式检查、却能被独立任务评估发现的错误样例。

末格把本次配置、逐轮记录与最终对照保存到当前目录的 results。改参数前可另存报告以便比较。
""")
add("code", """
out = Path("results")
out.mkdir(exist_ok=True)
report = dict(seed=SEED, budget_per_round=BUDGET, rounds=ROUNDS, initial=INITIAL,
              adaptive_history=history, comparisons=results)
path = out / "rsi_report.json"
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(path.resolve())
""")

notebook = dict(nbformat=4, nbformat_minor=5, cells=cells, metadata=dict(
    kernelspec=dict(name="python3", display_name="Python 3", language="python"),
    language_info=dict(name="python")))
Path(__file__).with_name("recursive_self_improvement.ipynb").write_text(
    json.dumps(notebook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
