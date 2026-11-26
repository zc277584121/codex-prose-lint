# Codex Prose Lint

给 Codex App 的回答加一轮表达检查：本地词表找出可能的防御性或否定表达，再由原会话中的 Codex 结合上下文复核。

已经更新配置，下一轮会使用新规则。~~不过，我无法保证每次回答都完全符合你的偏好。~~

复核范围是整条回答，防御性和偏防御性的表达都积极加上删除线。候选列表是参考建议，实际标注可以更多或更少；输出保留全部原文，只插入删除线符号。整个 hook 使用本地文本处理，安装时无需配置决策模型或 API key。

## 安装到 Codex App

准备好 [uv](https://docs.astral.sh/uv/getting-started/installation/)，然后运行：

~~~sh
uv tool install --python 3.12 'git+https://github.com/zc277584121/codex-prose-lint@v0.2.2'
export PATH="$(uv tool dir --bin):$PATH"
codex-prose-lint install
codex-prose-lint doctor
~~~

随后在 **App 设置 → Hooks** 中审核并信任 **Checking defensive prose**。如果页面尚未发现新钩子，重启 App；当前版本关闭 hooks 时，在 ~/.codex/config.toml 已有的 [features] 中设置 hooks = true。

安装器合并 ~/.codex/hooks.json，保留已有钩子并备份原文件。注册命令使用 Python 的绝对路径，App 可以直接调用；配置保存在 ~/.config/codex-prose-lint/config.toml，也支持 CODEX_HOME 和 XDG 目录设置。

## 升级已有安装

~~~sh
uv tool install --force --python 3.12 'git+https://github.com/zc277584121/codex-prose-lint@v0.2.2'
export PATH="$(uv tool dir --bin):$PATH"
codex-prose-lint --version
codex-prose-lint doctor
~~~

已有钩子继续使用同一个 uv 工具环境路径。Doctor 会显示实际运行版本、Python 路径、模块路径和已注册命令，便于核对源码与运行环境。

旧配置中的模型、阈值、API 密钥路径、超时和标注数量限制会被识别并忽略，具体字段显示在 doctor 的 ignored_legacy_settings 中。旧的密钥文件留在本机，当前版本不读取；configure-key 命令和 inspect 的 --live、--question 参数已移除。

## 一条回答怎样经过检查

回答结束时，Stop hook 读取 last_assistant_message，先保护代码、引用块、链接、HTML、表格和已有删除线，再按中英文标点切成短句。词表覆盖「不是、不会、避免、没有、并未、尚未、不要、不应、不足以、仅作、只涉及」及常见变体。

出现符合限制的候选时，hook 将候选按原文顺序随 block 提示交给 Codex，触发整条回答的复核。提示明确说明词面匹配可能多找或漏找，要求主动检查全文，将防御性、偏防御性和轻度防御性的措辞都加上删除线，包括候选列表之外的内容。

标注只插入删除线符号，保留所有原文、标点、空白和排版。一句话即使包含有用信息，其中的防御性措辞也可以标出，原文仍然可见；普通事实回答和引用例子按其实际语境判断。

闭合的双波浪号放在末尾标点之前，例如 `~~你好你好~~。`、`「~~仅供参考~~。」`。连续的末尾标点、引号和括号都保留在删除线外，并保持原有顺序；这条规则覆盖全部中英文标点。

Codex 随后完整输出带标注的回答，最多续写一次。原回答可能先流式显示；整条回答都没有防御性表达时，输出保持原样。

## 配置

| 配置项 | 默认值 | 用途 |
| --- | --- | --- |
| max_candidates | 36 | 每轮参考建议的数量上限，按原文顺序选取；最终标注数量独立判断。 |
| max_message_chars | 30000 | 最后一条回答的长度上限。 |
| max_clause_chars | 800 | 单个候选短句的长度上限。 |
| max_context_chars | 2400 | 本地 inspect 输出的上下文长度。 |
| mode | annotate | 自动续写复核；report 只显示候选提示。 |

扫描范围是最后一条回答。原会话为 Codex 提供复核上下文，脚本无需读取会话记录；通过 stop_hook_active 和本地去重记录限制为每轮一次续写。

## 本地查看候选

~~~sh
codex-prose-lint inspect examples/answer.zh.md
codex-prose-lint inspect examples/answer.zh.md --markdown
~~~

第一条显示候选、位置和命中词。第二条把全部词面候选加上删除线，便于预览位置；最终的删除线范围由 Codex 通读整条回答后决定。

诊断日志位于 ~/.local/state/codex-prose-lint/events.jsonl，记录运行版本、处理流程、候选数量和扫描耗时，不保存回答正文。

## 开发与验证

~~~sh
uv sync --locked --dev
uv run ruff check .
uv run pytest
uv run python evals/check_local.py
uv build
~~~

离线检查覆盖 58 条中文样本，包括独立的「不是」、跨标点的「不是……而是」，以及架构分类和 pgvector 选型的否定表达。自动化测试检查只加删除线的提示契约、超出候选范围的全文复核、无网络调用、旧配置兼容、Markdown 保护、原文位置、安装和续写去重。

App 的删除线显示已经在对话中确认。本次没有安排 TUI 或英文质量评测；早期的决策模型实验保留在 [历史报告](docs/evaluation.md) 和对应版本标签中。

## 卸载

~~~sh
codex-prose-lint uninstall
uv tool uninstall codex-prose-lint
~~~

配置和诊断记录留在本机供后续复用。完整实现说明见 [设计文档](docs/design.md)，版本变化见 [Changelog](CHANGELOG.md)。
