# 递归自我改进（RSI）中文实验课程

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB) ![JupyterLab](https://img.shields.io/badge/Notebook-JupyterLab-F37626) ![CPU 即可](https://img.shields.io/badge/Hardware-CPU-26735B)

从第一次运行 Python 代码开始，用六节课搭建一个能生成答案、检查答案并根据本轮结果安排下轮练习的系统。全程使用 CPU，可离线运行实验，首次安装 Jupyter 需要网络。

**第一次来？** 从[第一课](01_setup_and_first_run.ipynb)开始。已有 Jupyter 环境，可以从[课程首页](recursive_self_improvement.ipynb)选课。

## 🧭 这个实验怎样改进策略

以「从 8 前进三格」为例。如果当前策略抽到前进三格的规则，就会给出答案 1。校验通过后，这条规则的权重加一。同一批里各类题的失败次数，则用于自适应模式的下一轮出题。

```mermaid
flowchart LR
    A["抽题并生成答案"] --> B["校验整批答案"]
    B -->|"通过的样本"| C["更新解题规则权重"]
    B -->|"每类题的失败率"| D["调整出题比例（自适应模式）"]
    C --> A
    D --> A
```

## 🚀 第一次打开

在 Windows 文件资源管理器中打开本仓库，在地址栏输入 `powershell` 并回车。macOS 或 Linux 用户请在仓库目录打开终端。已经安装 Anaconda 的用户也可以从 Anaconda Prompt 进入本目录。

先输入 `python --version`。建议使用 Python 3.10 或更新版本。如果找不到命令，请安装 Python 3 并重新打开终端。然后逐行执行：

```sh
python -m pip install jupyterlab ipykernel
python -m ipykernel install --user --name rsi-course --display-name "Python (RSI)"
python -m jupyterlab 01_setup_and_first_run.ipynb
```

浏览器会打开第一课。若没有自动打开，请复制终端输出的本机网址到浏览器。右上角选择 **Python (RSI)**，点击第一个代码格，按 **Shift + Enter**。左侧 `[*]` 表示正在执行，变成数字后查看格子下方的输出。用 **Ctrl+S** 保存进度，下一课可从左栏双击打开。保留终端直到学习结束，退出时回到终端按 **Ctrl+C** 并按提示确认。

## 📚 学习路线

| 课次 | 课程 | 操作与验收 |
|---|---|---|
| 1 | [环境与第一次运行](01_setup_and_first_run.ipynb) | 算出 8 前进 3 格的结果，在 `results/first_run.txt` 里找到它 |
| 2 | [策略权重和采样概率](02_task_strategy_and_sampling.ipynb) | 把一条规则的权重加 10，对比理论概率和 1,000 次抽样计数 |
| 3 | [校验器与数据划分](03_verifier_and_data_splits.ipynb) | 检查三个集合的边界，用一个错答案测试校验器 |
| 4 | [追踪一轮训练](04_one_training_round.ipynb) | 跟踪 16 次采样，核对权重增量和通过数 |
| 5 | [递归反馈与公平对照](05_recursive_feedback.ipynb) | 给三种训练方法各 160 次采样，按种子比较期望与贪心正确率 |
| 6 | [失败诊断与毕业报告](06_failures_and_final_report.ipynb) | 用零权重和宽松校验器制造两种失败，读回含 12 组结果的报告 |

六课预计共 3 小时 20 分钟，含练习。每节都能从新内核启动。复做时一次只改一个参数并从头运行该课。第六课的 `results/final_report.json` 会在重跑时覆盖，要保留两次结果可先重命名。参考分数来自这个四规则算术任务，不能据此推断通用语言模型的自我改进能力。

## 🛠️ 遇到问题

- **提示找不到 rsi_lab**：第一课的“工作目录”应包含 `rsi_lab.py`。从仓库根目录启动 Jupyter，保持 Notebook 和该文件在同一目录。
- **提示变量未定义**：选择 **Kernel → Restart Kernel and Run All Cells**。每节课都要执行自己的导入格。
- **找不到结果文件**：查看保存格打印的绝对路径，在左栏刷新文件列表。
- **想核对实现**：打开 [实验函数](rsi_lab.py)。修改课程正文时编辑 [六课生成脚本](build_course.py)，再运行 `python build_course.py`。重建前另存自己的 Notebook 笔记。
