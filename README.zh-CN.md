# Codex Prose Lint

给 Codex App 的回答加一层防御性写作检查：找出多余的免责、限定和自我保护语句，再请 Codex 在原会话中输出带删除线的版本。

已经更新配置，下一轮会使用新规则。~~不过，我无法保证每次回答都完全符合你的偏好。~~

第一版只检查 `last_assistant_message`。脚本按标点切分短句、用固定词表挑出候选，再通过 **OpenRouter 的 Jev 1.14** 判断每个候选是否确属多余的防御性表达。达到阈值后，`Stop` hook 把可疑片段交回 Codex，由它复核并标注，最多续写一次。

## 安装到 Codex App

准备好 [uv](https://docs.astral.sh/uv/getting-started/installation/) 和 OpenRouter API key，然后在终端运行：

```sh
uv tool install --python 3.12 'git+https://github.com/zc277584121/codex-prose-lint@v0.1.0'
codex-prose-lint configure-key
codex-prose-lint install
codex-prose-lint doctor
```

`configure-key` 会隐藏输入，把密钥保存到本机权限为 `0600` 的文件。如果终端里已经有 `OPENROUTER_API_KEY`，可以用 `codex-prose-lint configure-key --from-env`。这样从桌面启动的 App 也能读取密钥，无需依赖终端环境的继承。

随后在 **Codex App 的 Hooks 设置**中，审核并信任新出现的 **Checking defensive prose**。如果 App 尚未发现新钩子，重启一次；以后钩子命令改变时，App 可能要求重新审核。

安装器会合并 `~/.codex/hooks.json`，保留已有的 MemSearch 等钩子，并给原文件留备份。它使用虚拟环境中 Python 的绝对路径，配置保存在 `~/.config/codex-prose-lint/config.toml`；支持自定义 `CODEX_HOME` 和 XDG 配置目录。

如果当前版本关闭了 hooks，在 `~/.codex/config.toml` 已有的 `[features]` 中设置 `hooks = true`，再重启 App。原生钩子的发现与信任流程见 [Codex 文档](https://learn.chatgpt.com/docs/hooks)。

## 显示效果和范围

原回答可能先流式显示，随后在同一个会话里出现带删除线的回答。修订提示只要求复核可疑片段并添加 `~~`，保持正文措辞和排版，不要求调用工具或修改文件。

文档内容、工具结果和子 Agent 输出都不在扫描范围。为了判断一句话是否与用户问题有关，默认会从本机记录中读取最近一条用户问题作为上下文；可以设置 `include_user_prompt = false` 关闭。

这一版面向 Codex App，删除线显示效果已在 App 对话中确认。没有进行 TUI 界面测试，也没有进行英文质量评测。

## 检测方式

中英文共用一套切分逻辑、词表和判别提示词。逗号、分号、冒号和句末标点用于切分候选，数字中的小数点、版本号及时间中的冒号会保留；代码、引用块、链接、HTML、表格和已有删除线会被排除。

候选可以只携带短句，也可以携带整句或所在段落。每个候选对应一个独立的 `noul` 问题，同一批问题合并到一次 OpenRouter 请求中；默认每批最多 12 个。

模型返回的是概率，阈值由程序判断。比如「无法连接数据库」可能是在报告真实故障；「不能保证所有情况都适用」也可能是在回答用户专门询问的限制，这些需要结合上下文保留。

## 调整配置

| 配置项 | 用途 |
| --- | --- |
| `threshold` | 默认 `0.8`，依据中文校准集选择；达到该值才交给 Codex 复核。 |
| `context_mode` | 默认 `paragraph`，也可选 `clause` 或 `sentence`。 |
| `batch_size` | 默认一次请求判断 12 个候选。 |
| `mode` | `annotate` 自动续写标注版；`report` 只显示钩子提示。 |
| `include_user_prompt` | 是否附带最近的用户问题。 |
| `env_file` | 指定已有的私密环境变量文件。 |

完整设置和默认限制见 [英文 README](README.md#configuration)。没有候选时不调用 API；接口或配置出错时放行原回答。通过 `stop_hook_active` 和本机去重记录避免反复续写。

## 查看检测结果

在源码目录运行：

```sh
uv sync --dev
uv run codex-prose-lint inspect examples/answer.zh.md
uv run codex-prose-lint inspect examples/answer.zh.md --live --question '配置改好了吗？'
uv run codex-prose-lint inspect examples/answer.zh.md --live --markdown --question '配置改好了吗？'
```

第一条检查命令只做本地切句和词表扫描。加上 `--live` 才调用 OpenRouter；`--markdown` 会输出程序直接插入删除线的预览，实际 hook 流程还会由 Codex 复核。

中文实验比较了短句、整句、整段三种输入，以及单次多问题、分开请求、问题逆序的差异。测试数据、原始分数和结论都在仓库内，详见 [评测报告](docs/evaluation.md)。

## 卸载

```sh
codex-prose-lint uninstall
uv tool uninstall codex-prose-lint
```

卸载会移除本项目的钩子，配置、密钥文件和诊断记录留在本机。
