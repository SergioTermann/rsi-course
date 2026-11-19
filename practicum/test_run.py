"""运行交接检查：python -m unittest discover -s practicum。"""
import json
import unittest
from unittest.mock import patch
from io import BytesIO

from practicum import run


class RoutingChecks(unittest.TestCase):
    def test_changed_id_does_not_hide_duplicate_text(self):
        row = run.read_split("seed")[0]
        with self.assertRaisesRegex(ValueError, "message"):
            run.audit([row, dict(row, id="copy")])

    def test_development_never_reads_test_split(self):
        original = run.read_split
        with patch.object(run, "read_split", wraps=original) as reads:
            snapshot = run.develop(None)
        self.assertEqual([args.args[0] for args in reads.call_args_list], ["seed", "pool", "dev"])
        reviewed = {r["id"] for t in snapshot["trace"] for r in t["generated"] if r["correct"]}
        seed_ids = {r["id"] for r in snapshot["seed"]}
        self.assertTrue(all(r["id"] in reviewed | seed_ids for r in snapshot["selected"]))

    def test_chinese_features(self):
        self.assertEqual(run.tokens("扣款，登录"), ["扣", "款", "扣款", "登", "录", "登录"])

    def test_course_reference(self):
        result = run.final(run.develop(None))
        self.assertEqual((run.hits(result["baseline"]), run.hits(result["candidate"])), (11, 12))
        self.assertEqual(result["regressions"], [])
        self.assertEqual(result["decision"], "shadow")

    def test_ollama_adapter_sends_only_query_text(self):
        response = BytesIO(json.dumps({'message': {'content': ' 账户 '}}).encode())
        with patch.object(run, "urlopen", return_value=response) as transport:
            predict = run.make_predictor(run.read_split("seed"), "example-model")
            self.assertEqual(predict("我的账号被锁定了"), "账户")
        req = transport.call_args.args[0]
        body = json.loads(req.data)
        self.assertEqual(body["messages"][-1], {"role": "user", "content": "我的账号被锁定了"})
        self.assertEqual(body["model"], "example-model")


if __name__ == "__main__":
    unittest.main()
