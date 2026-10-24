# Cursor 任务书：扩充开源题库——下载、归类、入库脚本（第二批：许可干净的数学数据集）

> 背景：项目已有题库管线：`dataset/题库/<学段>/<学科>/<年级>.json` 是规范化题库文件，单条记录 schema 为 `question_text / answer / solution / question_type / subject / education_level / grade / exam_type / knowledge_points / difficulty / source_url / teaching_tips`；`backend/import_open_math.py` 等脚本负责从 `dataset/题库/_原始下载/` 整理并**幂等导入**（按 question_text 去重）到 `QuestionBank` 表（见 `backend/models.py` 的 `QuestionBank`，先读它）。
> 本次只写脚本，**不要执行下载和导入**（网络下载由主控执行，避免超时）。不要动无关文件，不要 git commit。

## 1. 新增 `scripts/fetch_datasets.py`

按现有脚本风格写（requests + zipfile，无需第三方依赖；GitHub 直连下载，超时可重试 2 次）。下载到 `dataset/题库/_原始下载/<数据集名>/`：

| 数据集 | 来源 | 说明 |
|---|---|---|
| TAL-SCQ5K | `https://github.com/math-eval/TAL-SCQ5K`（GitHub zipball 或 releases；文件较大，含 cn/en 两个 json，用 cn 的） | MIT，小初高数学选择题 5K，含选项数组、逐步解析、知识点链、难度 0-4 |
| ape210k | `https://github.com/Chenny0808/ape210k`（train.ape.json 等） | MIT，小学数学应用题 21 万，question/equation/answer，无解析无年级 |
| math23k | `https://github.com/SCNU203/Math23k`（json 文件） | MIT，小学应用题 2.3 万，original_text/equation/ans，无解析无年级 |

脚本行为：已下载的文件跳过（幂等，重复运行只补缺失的）；下载完打印每个数据集的文件与条目数；无法下载的打印原因并继续下一个，不要整体退出。

## 2. 新增 `backend/import_open_round3.py`

仿照 `import_open_math.py` 的结构（先读它，复用其 `write_bank` / 去重 / 学段目录布局的写法；`_仅非商业` 目录这次不用，这批全是 MIT）：

- **TAL-SCQ5K-CN**：grade 字段映射学段（小学/初中/高中，按其 grade 数值，先抽样看数据再定映射，注释里写明依据）；question_type=选择题；选项格式化为现有题库的选项样式（参考 `format_choices`）；answer 取 answer_value；solution 用 answer_analysis；knowledge_points 用 knowledge_point_routes 拍平；difficulty 映射到 1-5（注释写明映射）；teaching_tips 写「来源 TAL-SCQ5K-CN，许可 MIT。竞赛/杯赛题，使用前请老师核对。」
- **ape210k / math23k**：question_text=question/original_text；answer=answer/ans；solution 留空（在 teaching_tips 注明「无官方解析」）；question_type=解答题；学段=小学；**grade 填 0 表示未分级**（exam_type 应用题）；difficulty 填 0 表示未知；teaching_tips 注明来源、MIT 许可、以及「来源网络爬取，含少量噪声，使用前请老师核对」。
- 写库文件与入库都幂等；ape210k 全量 21 万条入库前先打印总数并**抽样 2000 条写入 `dataset/题库/_抽检/ape210k_sample.json`**（人工质检用），正式导入仍然全量。
- 统计输出：按 学段/年级/题型 分组的数量，入库后 `question_bank` 表总行数增量。

## 3. 验证要求

- 两个脚本 `python -m py_compile` 通过。
- 用一个手工构造的 3 条小 JSON 走一遍 normalize 函数（在 `if __name__ == "__main__"` 里加 `--selftest` 子命令或单独自检函数，跑通即可，不用真数据）。

## 最终回复格式

脚本清单、各数据集字段映射表（尤其 TAL 的 grade 映射依据）、selftest 输出、你认为需要注意的风险点。
