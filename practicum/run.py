"""在仓库根目录运行 python practicum/run.py --help 查看用法。"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
from time import perf_counter
from urllib.request import Request, urlopen

DATA = Path(__file__).resolve().parent
OUT = DATA.parent / "results" / "routing"
LABELS = ("账单", "账户", "物流")


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def read_split(name):
    rows = [json.loads(line) for line in (DATA / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()]
    if not rows or any(row["label"] not in LABELS for row in rows):
        raise ValueError(f"数据为空或包含未知标签： {name}")
    return rows


def audit(rows):
    for field in ("id", "message"):
        keys = [r[field].strip().casefold() for r in rows]
        if len(set(keys)) != len(keys):
            raise ValueError(f"数据中发现重复字段 {field}")


def tokens(text):
    features = []
    for part in re.findall(r"[一-鿿]+|[a-z]+|[0-9]+", text.lower()):
        if "一" <= part[0] <= "鿿":
            # 相邻双字能保留“扣款”等线索，单字也能覆盖首次出现的组合。
            features.extend(part)
            features.extend(part[i:i + 2] for i in range(len(part) - 1))
        else:
            features.append(part)
    return features


def make_predictor(examples, model):
    if model:
        # 训练样例作为上下文示范。最终题只传 message，标签留在评估端。
        messages = [{"role": "system", "content":
                     "根据客户想解决的主要问题分派工单。只回答一个标签：账单、账户或物流。"}]
        for row in examples:
            messages.extend([{"role": "user", "content": row["message"]},
                             {"role": "assistant", "content": row["label"]}])

        def predict(message):
            body = dict(model=model, stream=False, options={"temperature": 0},
                        messages=messages + [{"role": "user", "content": message}])
            req = Request("http://127.0.0.1:11434/api/chat", data=json.dumps(body).encode(),
                          headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=120) as response:
                return json.load(response)["message"]["content"].strip().lower()
        return predict

    # 多项式朴素贝叶斯：按类别累计词频，加一平滑；三类使用相等先验。
    counts = {label: Counter() for label in LABELS}
    for row in examples:
        counts[row["label"]].update(tokens(row["message"]))
    vocab = set().union(*counts.values())
    totals = {label: sum(counts[label].values()) + len(vocab) for label in LABELS}

    def predict(message):
        words = [word for word in tokens(message) if word in vocab]
        return max(LABELS, key=lambda label: sum(
            math.log((counts[label][word] + 1) / totals[label]) for word in words))
    return predict


def score(examples, model, rows):
    predict = make_predictor(examples, model)
    records = []
    for row in rows:
        start = perf_counter()
        pred = predict(row["message"])
        records.append(dict(**row, prediction=pred, correct=pred == row["label"],
                            latency_ms=round((perf_counter() - start) * 1000, 3)))
    return records


def hits(records):
    return sum(row["correct"] for row in records)


def develop(model):
    seed, pool, dev = [read_split(s) for s in ("seed", "pool", "dev")]
    audit(seed + pool + dev)
    examples = seed.copy()
    best = examples.copy()
    baseline = score(seed, model, dev)
    best_hits = hits(baseline)
    trace = []
    for batch in (pool[:len(pool)//2], pool[len(pool)//2:]):
        generated = score(examples, model, batch)
        # 人工审核标签在这里充当校验器。模型猜错的样本不加入下一轮。
        accepted = [dict(id=r["id"], message=r["message"], label=r["prediction"])
                    for r in generated if r["correct"]]
        examples.extend(accepted)
        development = score(examples, model, dev)
        if hits(development) > best_hits:
            best, best_hits = examples.copy(), hits(development)
        trace.append(dict(generated=generated, dev=development))
    payload = dict(model=model, seed=seed, selected=best, baseline_dev=baseline,
                   trace=trace, dev_hits=best_hits, split_hashes={
                       k: fingerprint(v) for k, v in zip(("seed", "pool", "dev"), (seed, pool, dev))},
                   code_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    return payload


def final(payload):
    train_rows = []
    for split, digest in payload["split_hashes"].items():
        rows = read_split(split)
        if fingerprint(rows) != digest:
            raise ValueError(f"开发完成后，数据集 {split} 已发生变化")
        train_rows.extend(rows)
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != payload["code_hash"]:
        raise ValueError("实验代码已更改，请重新冻结候选版本")
    test = read_split("test")
    audit(train_rows + test)
    baseline, candidate = [score(payload[k], payload["model"], test) for k in ("seed", "selected")]
    wins = [b["id"] for a, b in zip(baseline, candidate) if b["correct"] and not a["correct"]]
    regressions = [b["id"] for a, b in zip(baseline, candidate) if a["correct"] and not b["correct"]]
    invalid = [b["id"] for b in candidate if b["prediction"] not in LABELS]
    # 小型作业的预注册门槛：至少多答对一题，同时没有逐题回退和非法输出。
    decision = "shadow" if wins and not regressions and not invalid else "hold"
    return dict(baseline=baseline, candidate=candidate, wins=wins, regressions=regressions,
                invalid=invalid, decision=decision, test_hash=fingerprint(test))


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["develop", "evaluate"])
    parser.add_argument("--run", required=True, help="实验名称，例如 first")
    parser.add_argument("--ollama", metavar="MODEL", help="开发时使用本地安装的 Ollama 模型")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run):
        parser.error("实验名称可使用英文字母、数字、下划线和连字符")
    folder = OUT / args.run
    frozen = folder / "frozen.json"
    report = folder / "evaluation.json"
    if args.stage == "develop":
        if frozen.exists():
            parser.error("该实验已经冻结，请换一个实验名称。")
        payload = develop(args.ollama)
        save(frozen, dict(payload=payload, digest=fingerprint(payload)))
        print(f"开发集答对题数：{hits(payload['baseline_dev'])} -> {payload['dev_hits']} / {len(payload['baseline_dev'])}")
        print(f"选中示范数：{len(payload['selected'])}，冻结文件：{frozen}")
    else:
        if args.ollama:
            parser.error("评估会使用开发时保存的模型")
        if not frozen.exists() or report.exists():
            parser.error("请先完成开发，每个实验仅评估一次")
        wrapper = json.loads(frozen.read_text(encoding="utf-8"))
        if fingerprint(wrapper["payload"]) != wrapper["digest"]:
            parser.error("冻结文件内容已改变")
        result = final(wrapper["payload"])
        result["frozen_digest"] = wrapper["digest"]
        save(report, result)
        print(f"测试集答对题数：{hits(result['baseline'])} -> {hits(result['candidate'])} / {len(result['candidate'])}")
        print("评审决定：", {'shadow': '进入影子验证', 'hold': '暂缓发布'}[result["decision"]], "改善题号：", result["wins"], "回退题号：", result["regressions"])
        print(report)


if __name__ == "__main__":
    main()
