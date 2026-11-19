# 第 8 课 · 从基线到候选版本（约 75 分钟）

这里训练的是能直接运行的词频分类器。它把英文文本拆词，分别统计每类里见过哪些词，再根据一条新工单里的词给三类打分。每类先验相等，未在训练词表出现的词跳过。全是陌生词时，三类同分，程序会选排在最前面的 billing。找到这类具体行为，比记住算法名称更有用。

## 亲手调用预测接口

从仓库根目录运行 `python`：

```python
from practicum.run import read_split, make_predictor, score, hits
seed, dev = read_split("seed"), read_split("dev")
route = make_predictor(seed, model=None)
print(route("forgot password"))
print(route("xyzzy"))
rows = score(seed, None, dev)
print(hits(rows), len(rows))
print([(r["id"], r["message"], r["prediction"], r["label"]) for r in rows if not r["correct"]])
```

默认基线答对 5/6。找到 dev-04，检查种子中是否见过 authentication、link、expired。写下一条可以被实验证伪的假设，再退出 Python。

## 执行两轮反馈

```sh
python practicum/run.py develop --run first
```

每轮先用当前策略预测练习题，把预测与人工标签一致的样本加入下一轮，用扩大的示范集重新拟合策略。两轮都用同一开发集打分；相同分数时保留较早版本。人工标签是这个实验的外部监督成本。没有这些标签，不能把这条流程照搬成“模型自己认证正确”。

打开 `results/routing/first/frozen.json`。在 `payload.trace[0].generated` 查看每条预测，再对照 `payload.selected`。默认首轮保留 pool-01、02、04；第二轮也有正确样本，但开发成绩没有超过第一轮。最终选中 9 条示范（6 条种子加 3 条），没有把全部 12 条都交给最终评估。文件里的摘要用于检查实验内容是否意外变化。

## 加一个必要对照

既然练习池已经有人工标签，直接把所有标签拿来监督训练也很合理。重新打开 Python，运行：

```python
from practicum.run import read_split, score, hits
s, p, d = [read_split(k) for k in ("seed", "pool", "dev")]
for name, examples in [("seed", s), ("all reviewed", s+p)]:
    records = score(examples, None, d)
    print(name, len(examples), hits(records), "/", len(records))
```

默认全监督对照也是 6/6。在这份开发数据上，两种做法打平；要决定是否值得维护筛选循环，还需比较标签取得方式、推理调用与维护成本。这里改进的是策略使用的示范集，筛选算法和评价标准仍由工程师设定。三种方案（基线、筛选反馈、全部监督）各用了多少标签、保留了多少样例、开发成绩如何？这里对照的可用标签相同，实际用于拟合的样本数量不同，不能据此把收益全归因于递归。**验收**：写出一个被拒绝的练习样本，以及如果撤掉人工校验，它会强化哪一种错派。

继续学习 [第 9 课](09_model.md)。
