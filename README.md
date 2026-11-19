# 递归自我改进（RSI）实验课

当同一个策略既生成答案，又影响下一轮的练习内容时，怎样判断它真的学得更好了？这门中文交互课用一个可以逐轮检查的算术任务，带你比较一次更新、多轮更新和自适应出题。预计 25 分钟。实验仅使用 Python 标准库，在 CPU 上运行。

## 开始学习

在仓库目录中运行以下命令，然后在 JupyterLab 里选择 Python 3 内核，从第一格开始按 Shift + Enter。已有 Jupyter 环境可直接打开 [课程 Notebook](recursive_self_improvement.ipynb)。

```sh
uv run --with jupyterlab --with ipykernel jupyter lab recursive_self_improvement.ipynb
```

## 动手实验

1. 测量初始策略的期望正确率与贪心正确率。
2. 检查一轮训练里每类题的尝试数、通过数，以及下一轮分配给弱项的练习机会。
3. 固定总预算为 160 次采样，比较三种训练方法，并用冻结策略作基线。
4. 把某条正确规则的初始权重设为零，观察提高出题频率能否帮助策略发现它。

最后一格把本轮配置和分组成绩写入 `results/rsi_report.json`。仓库附带一份[默认参数的参考结果](reference/rsi_report.json)，可供核对。

维护课程正文时编辑 `build_rsi.py`，再运行 `python build_rsi.py` 重新生成无输出的 Notebook。
