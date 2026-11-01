# Document to Anki

**把 PDF、Word、扫描讲义和题库，变成真能背下来的 Anki 卡片。**

这是一个 AI Skill。它让 AI 先逐题校对资料，再把答案拆成三层记忆结构，最后生成可以直接导入 Anki 的牌组，并如实报告验证到了哪一步。适合各类课程和资格考试，尤其是需要背诵的简答题、名词解释、比较题和论述题。

**[查看介绍页](https://wenyuye001-lang.github.io/document-to-anki-skill/)**

## 你会拿到什么

| 文件 | 用途 |
| --- | --- |
| `.apkg` 完整牌组 | 自带正反面模板和样式，导入即用 |
| `.csv` 备用文件 | `Front`、`Back`、`Tags` 三列 |
| 原题覆盖及校对清单 | 每道题已制卡、已排除或待核对的状态 |
| 导入与验收说明 | 写明实际验证到了哪一级 |

## 它和直接让 AI 做卡片有什么不同

- **先校对，再制卡**：排查 OCR 错误和跨题串入，不确定的内容标注页码，交给人工核对。
- **三层记忆结构**：L1 关键词、L2 分论点、L3 完整答案，关键词不会取代完整作答。
- **三种卡片**：总框架卡考结构，分论点卡考要点，整题论述卡考完整输出，不机械地按段落切卡。
- **分级报告验证结果**：生成、静态检查、实际导入、正反面显示分开说明，不把“文件生成了”说成“能用了”。

## 快速开始

### Claude Code

```bash
git clone https://github.com/wenyuye001-lang/document-to-anki-skill.git
mkdir -p ~/.claude/skills
cp -r document-to-anki-skill/document-to-anki ~/.claude/skills/
```

### 其他 AI 工具

安装 `document-to-anki` 文件夹，或把其中的 `SKILL.md` 作为附件上传。

然后上传复习资料并发送：

> 请严格执行我提供的 `document-to-anki` Skill，将附件整理为适合 Anki 的复习卡片。先建立题目索引，按原文逐题核对；将答案归纳成一级关键词、二级分论点、三级完整作答；制作总框架卡、语义明确的分论点卡以及必要的整题论述卡。请优先生成带 `Front/Back` 正反面模板的 APKG，提供 CSV 备用，报告识别/校对风险。必须分别说明文件静态检查、Anki 实际导入及正反面显示的验证状态；不能把生成成功冒充导入成功。若无法运行 Anki，请提供我可以在手机或电脑上操作的最终验收步骤。

## 仓库结构

```text
document-to-anki/                  # Skill 本体，安装这个文件夹
├── SKILL.md                       # 主流程与规则
├── README.md                      # 使用说明
├── references/
│   ├── acceptance-checklist.md    # 三级验收与交付清单
│   ├── troubleshooting.md         # 常见错误与解决方法
│   └── verified-success-case.md   # 已验证的案例及局限
└── scripts/
    └── verify_apkg.py             # 旧式 APKG 静态检查脚本
docs/index.html                    # 介绍页
```

## 使用前请注意

- 首次导入新牌组前先备份，或导入隔离牌组测试，不要直接覆盖已有复习记录。
- 仓库记录的成功案例，只代表那一份牌组在当时环境下导入和翻面正常，每份新资料都要重新验收。
- `verify_apkg.py` 只做静态检查，不能代替 Anki 实际导入测试。
- 技术验收通过不代表答案逐字无误，扫描资料需要单独核对内容。
