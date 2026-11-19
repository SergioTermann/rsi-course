"""Generate the six editable, self-contained RSI course notebooks."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
cells = []
course_file = ""


def add(kind, source):
    cells.append(dict(cell_type=kind, id=f"{course_file[:2]}-{len(cells):02}",
                      metadata={}, source=source.strip().splitlines(keepends=True),
                      **({"execution_count": None, "outputs": []} if kind == "code" else {})))


def md(text):
    add("markdown", text)


def code(text):
    add("code", text)


def save():
    md("[返回课程首页并选择下一节](课程首页.ipynb)")
    notebook = dict(nbformat=4, nbformat_minor=5, cells=cells.copy(), metadata=dict(
        kernelspec=dict(name="python3", display_name="Python 3", language="python"),
        language_info=dict(name="python", version="3.12")))
    (ROOT / course_file).write_text(
        json.dumps(notebook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cells.clear()


def start(number, title, minutes, goal, concepts, guide):
    md(f"""# 第 {number} 课 · {title}

**本课用时约 {minutes} 分钟。** {goal}

## 学完后你能做到

{concepts}

## 跟着操作

{guide}

运行代码格时，把光标放在格子里，按 **Shift + Enter**。看到输出后再运行下一格。若第一次误点或修改了上方变量，选 Jupyter 菜单里的 **Kernel → Restart Kernel and Run All Cells**，从第一格重新运行。本课不要求预先懂强化学习，也不需要 GPU。
""")


course_file = "01_环境与第一次运行.ipynb"
start(1, "安装环境与第一次运行", 20,
      "在自己的电脑上打开课程、运行 Python、保存实验结果。",
      "- 确认 Python 内核正在运行。\n- 运行一道带校验的简单题。\n- 找到工作目录并从中读回自己的第一份记录。",
      "1. 从课程首页点进本课，找到下面第一段带 [ ] 的代码格。\n2. 在页面右上角选择已安装的 Python 3 内核。\n3. 从上到下运行每格，找到打印工作目录的代码格，确认那里有 rsi_lab.py。")
md("""## 为什么先从小任务开始

本课程用四种确定的移动规则完成个位数运算。规则、数据和校验器都能直接检查，因此你可以先弄清反馈循环的行为，再把问题带回语言模型训练。

推荐环境是 Python 3.10 或更新版本。JupyterLab 不是算法依赖，只是交互界面。联网安装命令如下，运行后保持终端打开：

```sh
python -m pip install jupyterlab ipykernel
python -m ipykernel install --user --name rsi-course --display-name "Python (RSI)"
jupyter lab
```

Jupyter 打开后，用文件浏览器进入本仓库，点击本课 Notebook。也可直接用 VS Code 安装 Jupyter 扩展并打开 Notebook。Notebook 的执行输出在内核里产生，保存 Notebook 会保留代码和结果。""")
code("""from pathlib import Path
import sys

print("Python:", sys.version.split()[0])
print("工作目录:", Path.cwd())
assert sys.version_info >= (3, 10), "需要 Python 3.10 或更新版本"
print("环境检查通过")""")
md("""如果代码格左侧从 `[ ]` 变为 `[1]`，说明第一次运行成功。若内核选单里没有课程环境，关闭 Jupyter，重新运行上面的 ipykernel 安装命令再启动。

下面用心算检查「起点加步数，取个位」的题目。""")
code("""start_digit, steps = 8, 3
correct_answer = (start_digit + steps) % 10
print(f"从 {start_digit} 前进 {steps} 格，个位数是 {correct_answer}")
assert correct_answer == 1""")
md("""本仓库的分课从第二课开始会要求你运行本地 Python 文件。下一格确认 Python 能导入课程实验模块，并检查「前进三格」的规则。""")
code("""import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from rsi_lab import NAMES, answer, verified

print("四条候选规则:", NAMES)
assert answer(8, 2) == 1 and verified(8, 2, 1)
print("模块导入与答案校验通过")""")
md("""## 把本次结果留在硬盘上

运行下一格后，在 Jupyter 左侧双击 results，再打开 first_run.txt。它记录了刚才的答案。把第一道题的起点换成 9、预期答案改为 2，再运行计算和保存两格，检查文件里是否也变成了 2。""")
code("""folder = Path("results")
folder.mkdir(exist_ok=True)
# 在左侧文件栏可按同一路径打开这份记录。
record = folder / "first_run.txt"
record.write_text(str(correct_answer), encoding="utf-8")
assert int(record.read_text(encoding="utf-8")) == correct_answer
print("已保存:", record.resolve())""")
md("""## 自检

- [ ] Python 版本为 3.10 或更新。
- [ ] 我能在 Jupyter 中看到带执行编号的结果。
- [ ] 算术答案是 1，校验结果通过。
- [ ] 我知道怎么重启内核、重新从头执行。

**完成后保存 Notebook。** 检查工作目录里的 `results` 文件夹。本课保存 first_run.txt，第六课保存 final_report.json。若这节所有格子都通过，你已准备好进入第二课。""")
save()


course_file = "02_策略与采样概率.ipynb"
start(2, "任务、策略与采样", 30,
      "拆开一道题里的任务、候选解题规则和策略抽样。",
      "- 追踪一次策略如何挑选候选规则。\n- 解释权重变化如何改变抽样概率。\n- 说明固定随机种子解决了什么问题。",
      "运行代码后，手动修改最后一段中的一个权重，重跑本节并比较概率。")
md("""## 任务与策略是两件事

题目的**任务**由「起点」和「指令」组成。候选规则是前进一格、两格、三格或后退一格。策略不直接存答案，而是给候选规则配权重，然后按权重比例抽取规则。

权重是正数也可以是整数计数。比如 `[5, 2, 1, 1]` 的总权重是 9，第一条规则被选中的概率是 5/9。采样引入随机性，同一策略有时会给出不同回答。""")
code("""import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from rsi_lab import INITIAL, MOVES, NAMES, answer

task = 0
weights = INITIAL[task]
total = sum(weights)
print("题目:", NAMES[task])
for name, weight in zip(NAMES, weights):
    print(f"{name}: 权重 {weight}, 抽中概率 {weight / total:.1%}")
print("各规则在起点 8 的答案:", [answer(8, rule) for rule in range(len(MOVES))])""")
md("""观察输出后，自己判断哪条规则最容易被抽到。在下一格里用固定随机种子抽 1,000 次。相同的种子和权重应该得到相同的计数。""")
code("""import random

rng = random.Random(19)
draws = rng.choices(range(len(weights)), weights=weights, k=1000)
counts = [draws.count(rule) for rule in range(len(weights))]
print(dict(zip(NAMES, counts)))
assert draws == random.Random(19).choices(range(len(weights)), weights=weights, k=1000)""")
md("""现在改大一个候选规则的权重，观察抽样分布怎样改变。每次改完都重置种子，这样可把权重变化与随机序列变化区分开。""")
code("""# 复制后只改一项，原始概率仍可用于比较。
changed = weights.copy()
changed[2] += 10
old_prob = weights[2] / sum(weights)
new_prob = changed[2] / sum(changed)
print(f"{NAMES[2]} 的抽样概率: {old_prob:.1%} -> {new_prob:.1%}")
new_draws = random.Random(19).choices(range(len(changed)), weights=changed, k=1000)
print("前进三格的实际次数:", counts[2], "->", new_draws.count(2))
assert new_prob > old_prob""")
md("""## 自检

- [ ] 权重加总得到策略的归一化分母。
- [ ] 增加某条规则的权重会提高它的采样概率。
- [ ] 固定随机种子便于重复实验，但不会让模型更聪明。
- [ ] 我能指出哪个输入表示任务，哪个输入表示策略。

接下来会问一个重要问题：我们怎样知道抽到的答案是正确的？""")
save()


course_file = "03_校验器与数据划分.ipynb"
start(3, "校验器、训练集与独立评估", 35,
      "理解反馈循环里的答案校验和数据分区，并亲自检查数据泄漏。",
      "- 用规则计算答案是否正确。\n- 解释训练、开发、测试数据分别做什么。\n- 理解训练奖励正确时为何还要固定测试题。",
      "运行内置自检，试着把错误答案改为正确答案，再观察校验结果。")
md("""## 校验器决定什么能教会策略

本练习有精确的规则校验器。它将模型预测与指令对应的正确数字比较。通过的样本给所用规则增加权重，未通过的样本不更新。这代表一种带外部反馈的学习循环。

真实语言任务的奖励通常更难设计。若校验器只看 JSON 格式，语法正确但事实错误的答案也可能获奖励。后面的练习会专门检查这个反馈漏洞。""")
code("""import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from rsi_lab import TRAIN, DEV, TEST, answer, verified

examples = [(8, 2, 1), (8, 2, 9), (0, 3, 9)]
for x, task, prediction in examples:
    print(x, task, prediction, "通过" if verified(x, task, prediction) else "未通过")
assert [verified(*item) for item in examples] == [True, False, True]""")
md("""把 100 个起点划成三个互斥部分。训练集可用于产生训练样本，开发集用于观察每轮变化，测试集留到策略选择完成之后作最终报告。这次按起点连续分段。这些数字题存在周期结构，因此它只能演示隔离流程，不能证明真实任务的分布泛化。""")
code("""print("训练:", min(TRAIN), max(TRAIN), len(TRAIN))
print("开发:", min(DEV), max(DEV), len(DEV))
print("测试:", min(TEST), max(TEST), len(TEST))
# 交集非空表示有起点同时出现在两个集合中。
assert not set(TRAIN) & set(DEV)
assert not set(TRAIN) & set(TEST)
assert not set(DEV) & set(TEST)
assert len(TRAIN) + len(DEV) + len(TEST) == 100""")
md("""## 做一个校验器反例

给验证函数一个错误答案。如果它仍通过，就意味着奖励信号并未识别这项错误，后续优化可能朝错误目标前进。这里使用精确算术校验，预期错误答案必须被拒绝。""")
code("""x, task, wrong = 8, 2, 9
assert wrong != answer(x, task)
assert not verified(x, task, wrong)
print("错误答案被拒绝。训练反馈与任务正确性在这个小环境中一致。")""")
md("""## 自检

- [ ] 三个集合没有重叠。
- [ ] 错误答案被校验器拒绝。
- [ ] 我能解释为什么每轮比较要用同一套开发题。
- [ ] 我知道最终测试集不应用来反复挑选参数。

下一课会逐轮运行训练，并从记录里读出反馈过程。""")
save()


course_file = "04_追踪一轮训练.ipynb"
start(4, "跑完并读懂一轮训练", 35,
      "逐批执行采样、校验、策略更新，并按指令解释一轮结果。",
      "- 查看一批采样前后的权重差。\n- 区分尝试数、正确样本数与开发集准确率。\n- 识别一轮训练里没有收集到正样本的组。",
      "先运行小批次，再将预算从 16 改成 64，比较随机波动。")
md("""## 一次更新发生在哪里

本课将一批经历记录成 `(指令, 起点, 选择的规则, 模型答案)`。先用旧策略完整采样，然后统一检查这批轨迹。每个通过校验的轨迹给对应规则加一。更新是在一整批结束后发生，因此本批后半段不会使用刚刚更新的权重。""")
code("""import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from rsi_lab import INITIAL, TRAIN, evaluate, sample_batch, update
import random

rng = random.Random(19)
batch = sample_batch(rng, INITIAL, [1, 1, 1, 1], budget=16)
# 此时 16 个答案都已生成，下面的更新只会影响下一批。
updated, attempts, kept = update(INITIAL, batch)
assert sum(attempts) == len(batch)
assert [sum(new) - sum(old) for new, old in zip(updated, INITIAL)] == kept
print("首条轨迹 (指令, 起点, 规则, 答案):", batch[0])
print("尝试:", attempts)
print("通过:", kept)
print("权重变化:")
for name, before, after in zip(("前进一步", "前进两格", "前进三格", "后退一步"), INITIAL, updated):
    print(name, before, "->", after)""")
md("""尝试数回答「这类题出现了几次」，通过数回答「有几条正反馈」，权重差回答「策略被哪些正样本改变」。某一组的通过数为零时，这轮就没有正样本能教会它。后续轮次能否恢复取决于它是否还会被抽到、能否探索到正确候选。""")
code("""before = evaluate(INITIAL, range(50, 75))
after = evaluate(updated, range(50, 75))
print(f"开发集期望正确率: {before['expected']:.1%} -> {after['expected']:.1%}")
for name, old, new in zip(("前进一步", "前进两格", "前进三格", "后退一步"),
                          before["by_task"], after["by_task"]):
    print(f"{name}: {old:.1%} -> {new:.1%}")""")
md("""期望正确率按各候选被抽中的概率计分。例如正确规则占 2/10，这道题就有 20% 的答对机会。贪心正确率只看权重最大的规则，遇到并列取第一条。正确规则权重增长但仍未排第一时，两种指标会有怎样的变化？\n\n同一预算重复运行但换随机种子，可以看到有限样本下结果不同。记录种子、预算和本批通过数，才能解释结果差异。不要只选得分最高的一次。""")
code("""for seed in (19, 20, 21):
    local_rng = random.Random(seed)
    local_batch = sample_batch(local_rng, INITIAL, [1, 1, 1, 1], budget=16)
    local_weights, local_attempts, local_kept = update(INITIAL, local_batch)
    print(seed, "通过", local_kept, "开发期望", round(evaluate(local_weights, range(50, 75))["expected"], 3))""")
md("""## 自检

- [ ] 更新后的权重只因通过校验的样本改变。
- [ ] 预算和尝试数不是正确样本数。
- [ ] 评估比较使用固定开发集。
- [ ] 我能为一个没有得到正样本的组提出失败原因。

下一课把训练分成多轮，看策略更新和练习分配如何形成递归反馈。""")
save()


course_file = "05_递归反馈与公平对照.ipynb"
start(5, "把一轮训练变成递归反馈", 40,
      "对比冻结、一次训练、多轮均匀训练和按弱项调整训练分布。",
      "- 对照相同训练预算下的多种策略。\n- 读出弱项如何影响下一轮练习分配。\n- 用多个随机种子报告变化范围，而不是挑单次高分。",
      "运行固定种子的完整比较，再用自己的种子列表复做。")
md("""## 每轮有两条反馈

训练数据是否通过校验会改变**解题策略**。这一轮哪种指令经常失败，会改变**下一轮抽什么题**。均匀课程只更新解题策略，固定下一轮练习比例。自适应课程根据各组平滑失败率分配下一轮样本。

自适应权重为 `(失败数 + 1) / (尝试数 + 2)`。平滑项使没有尝试的组仍然有正权重，避免整组永久消失。模型仍必须能抽到正确解题规则。""")
code("""import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from rsi_lab import INITIAL, NAMES, evaluate, train

model, trace = train(seed=19, adaptive=True, budget=32, rounds=5)
for row in trace:
    print("轮", row["epoch"], "尝试", row["attempts"], "通过", row["kept"])
    print("开发集各组:", [round(v, 2) for v in row["dev"]["by_task"]])""")
md("""先逐行看五轮记录。若一组的平滑失败率高于其他组，它下一轮被抽中的概率就更高，实际抽到的次数仍会波动；若正样本改变了策略，该组后续可能更容易答对。多轮均匀对照可以单独检验「中途更新策略」的作用，自适应对照再检验「按失败调整数据」的额外作用。""")
code("""settings = [
    ("冻结", False, 0, 0),
    # 160 × 1 和 32 × 5 使用相同预算，差异来自何时更新策略。
    ("一次更新", False, 160, 1),
    ("多轮均匀", False, 32, 5),
    ("多轮自适应", True, 32, 5),
]
for seed in (19, 20, 21):
    for label, adaptive, budget, rounds in settings:
        weights, _ = train(seed, adaptive, budget, rounds)
        score = evaluate(weights, range(75, 100))
        print(seed, label, "期望", f"{score['expected']:.1%}",
              "贪心", f"{score['greedy']:.1%}",
              "最弱组", f"{min(score['by_task']):.1%}")""")
md("""从**同一个种子的一组对照**开始解释。多轮均匀与一次更新使用相同总样本预算，差别在更新频率；多轮自适应与多轮均匀差在课程调整。再横向比较种子，判断观察是否稳健。这个有限、确定性答案空间里，均匀和自适应可能非常接近，不应强行宣称自适应一定更好。""")
code("""from rsi_lab import next_mix

attempts, kept = [10, 10, 10, 10], [8, 5, 2, 0]
mix = next_mix(attempts, kept)
print(dict(zip(NAMES, [round(x / sum(mix), 3) for x in mix])))
assert mix[-1] > mix[0]""")
md("""## 自检

- [ ] 多轮训练的总采样预算为 160。
- [ ] 每轮改进使用固定开发集测量。
- [ ] 我能解释两条反馈路径分别改变什么。
- [ ] 我会用种子配对的对照结果，而不拿不同种子直接作因果比较。

第六课会做反事实实验、检查奖励漏洞，并整理一份可复现报告。""")
save()


course_file = "06_失败诊断与毕业报告.ipynb"
start(6, "失败诊断、奖励漏洞与课程验收", 40,
      "挑战课程的假设，观察探索失败，并产出一份可供复核的实验记录。",
      "- 说明增加弱项训练量为何无法解决策略零概率探索。\n- 构造一个错误却会被宽松验证器奖励的例子。\n- 保存完整的配置、过程数据和最终成绩。",
      "先写下每个反事实格子的预测，再运行代码核对。")
md("""## 诊断一：训练数据再多也看不到的规则

若某指令对应的正确规则初始权重为零，按权重采样永远不会选中它。因为只有正确样本才加权，策略无法靠自己的更新跨出这个零概率状态。这是探索与反馈设计的限制，不是练习次数不足。

把第三组（「前进三格」指令）正确候选的权重设成零。比较冻结权重、原始策略、训练后的策略。""")
code("""import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from rsi_lab import INITIAL, NAMES, evaluate, train

broken = [row.copy() for row in INITIAL]
# 第三行是「前进三格」题，第三列正是它需要的规则。
broken[2][2] = 0
for row in broken:
    assert sum(row) > 0
weights, trace = train(seed=19, adaptive=True, initial=broken, budget=128, rounds=8)
print("前进三格正确候选权重:", broken[2][2], "->", weights[2][2])
print("这一组开发期望正确率:", evaluate(weights, range(50, 75))["by_task"][2])
assert weights[2][2] == 0""")
md("""提高弱项出题比例不会帮助这个策略找到自己永远不会提出的解。系统需要另一种来源的正确答案，例如示范数据、可验证的候选生成或非零探索概率。请先为每种补救方式写下新的风险，再修改代码验证。""")
md("""## 诊断二：奖励与真正目标错位

把精确正确性验证器换成只要求答案落在 0 到 9 之间的格式验证器。对题目「8 前进 3 格」，答案 9 是有效数字，却是错误答案。宽松验证器会把它保留并加强错误规则。""")
code("""from rsi_lab import verified

def format_only(x, task, prediction):
    return isinstance(prediction, int) and 0 <= prediction <= 9

x, task, wrong = 8, 2, 9
print("正确性验证:", verified(x, task, wrong))
print("格式验证:", format_only(x, task, wrong))
assert not verified(x, task, wrong) and format_only(x, task, wrong)""")
code("""for label, check in [("精确", verified), ("只查格式", format_only)]:
    result, rows = train(19, True, verifier=check)
    passed = sum(sum(row["kept"]) for row in rows)
    actual = evaluate(result, range(50, 75))["expected"]
    print(f"{label}：160 个样本中保留 {passed} 个，独立评估期望正确率 {actual:.1%}")""")
md("""真实 LLM 训练中，「回答能被解析」只说明通过协议约束，不代表推理结论正确。请把这一反例改成你领域里的一个奖励漏洞，并设计一个独立可运行的验证。""")
md("""## 保存并核验实验记录

记录文件包含随机种子、预算、轮数、逐轮样本数以及四种方法在多个种子上的测试成绩。最终测试集用于报告，不应拿它反复选择训练参数。""")
code("""import json
from pathlib import Path
from rsi_lab import INITIAL, train, evaluate

runs = []
for seed in (19, 20, 21):
    for name, adaptive, budget, rounds in [
        ("冻结", False, 0, 0),
        ("一次更新", False, 160, 1),
        ("多轮均匀", False, 32, 5),
        ("多轮自适应", True, 32, 5),
    ]:
        weights, trace = train(seed, adaptive, budget, rounds)
        runs.append(dict(seed=seed, mode=name, budget=budget, rounds=rounds, adaptive=adaptive, weights=weights, history=trace,
                         test=evaluate(weights, range(75, 100))))

output = Path("results")
output.mkdir(exist_ok=True)
report = dict(initial=INITIAL, runs=runs, note="本报告来自四规则算术实验，适用于分析当前任务的反馈机制。")
path = output / "final_report.json"
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
loaded = json.loads(path.read_text(encoding="utf-8"))
assert len(loaded["runs"]) == 12
assert all(len(run["history"]) == (0 if run["mode"] == "冻结" else 1 if run["mode"] == "一次更新" else 5)
           for run in loaded["runs"])
print(path.resolve(), "包含", len(loaded["runs"]), "组完整实验")""")
md("""## 用报告回答一个问题

在 Jupyter 左栏打开 results/final_report.json，找到 seed 为 19、mode 为 多轮自适应 的记录。test.expected 是最终期望正确率，history 中的 kept 是每轮通过数。用同种子 多轮均匀 的 test.expected 作差，乘 100 得到百分点差值。种子 19 应约为 +2.5 个百分点；再算种子 21，检查方向是否一致。

## 课程毕业清单

- [ ] 能从零启动 Jupyter 并选择 Python 内核。
- [ ] 能说明策略权重、奖励校验和训练分布的作用。
- [ ] 能从同种子结果分解多轮更新与自适应采样的作用。
- [ ] 能解释零概率探索失败和格式奖励漏洞。
- [ ] 能从头运行全部课，并找到 `results/final_report.json`。
- [ ] 已保存最终报告与 Notebook。

**课程边界：** 本仓库是一套 RSI 学习实验，用明确的规则模拟「生成、筛选、更新、再生成」的迭代反馈。它不连接外部 LLM，也不代表自主改写代码、模型权重或目标函数的完整 RSI 系统。将实验迁移到 verl 前，必须另行设计正确的任务奖励、独立测试集和安全回归集。
""")
code("""print("RSI 六课验收完成。")""")
save()


if __name__ == "__main__":
    print("六节课程笔记本已生成，目录为", ROOT)
