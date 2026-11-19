"""Run from the repository root: python practicum/run.py --help."""
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
LABELS = ("billing", "access", "delivery")


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def read_split(name):
    rows = [json.loads(line) for line in (DATA / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()]
    if not rows or any(row["label"] not in LABELS for row in rows):
        raise ValueError(f"Invalid labels or empty split: {name}")
    return rows


def audit(rows):
    for field in ("id", "message"):
        keys = [r[field].strip().casefold() for r in rows]
        if len(set(keys)) != len(keys):
            raise ValueError(f"Duplicate {field} across splits")


def tokens(text):
    return re.findall("[a-z]+", text.lower())


def make_predictor(examples, model):
    if model:
        # 训练样例作为上下文示范。最终题只传 message，标签留在评估端。
        messages = [{"role": "system", "content":
                     "Route the customer's main issue. Reply with exactly one label: billing, access, delivery."}]
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
            raise ValueError(f"{split} changed since development")
        train_rows.extend(rows)
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != payload["code_hash"]:
        raise ValueError("Runner changed since development; freeze a new run")
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
    parser.add_argument("--run", required=True, help="New experiment name, e.g. first")
    parser.add_argument("--ollama", metavar="MODEL", help="Use a locally installed Ollama model during development")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run):
        parser.error("Use letters, digits, underscores or hyphens in the run name")
    folder = OUT / args.run
    frozen = folder / "frozen.json"
    report = folder / "evaluation.json"
    if args.stage == "develop":
        if frozen.exists():
            parser.error("Run already frozen. Use a new name.")
        payload = develop(args.ollama)
        save(frozen, dict(payload=payload, digest=fingerprint(payload)))
        print(f"Dev: {hits(payload['baseline_dev'])} -> {payload['dev_hits']} / {len(payload['baseline_dev'])}")
        print(f"Selected examples: {len(payload['selected'])}. Frozen: {frozen}")
    else:
        if args.ollama:
            parser.error("Evaluation uses the model saved at development time")
        if not frozen.exists() or report.exists():
            parser.error("Develop first and evaluate each run once")
        wrapper = json.loads(frozen.read_text(encoding="utf-8"))
        if fingerprint(wrapper["payload"]) != wrapper["digest"]:
            parser.error("Frozen file changed")
        result = final(wrapper["payload"])
        result["frozen_digest"] = wrapper["digest"]
        save(report, result)
        print(f"Test: {hits(result['baseline'])} -> {hits(result['candidate'])} / {len(result['candidate'])}")
        print("Decision:", result["decision"], "Wins:", result["wins"], "Regressions:", result["regressions"])
        print(report)


if __name__ == "__main__":
    main()
