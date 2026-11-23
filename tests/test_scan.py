import pytest

from codex_prose_lint.scan import annotate, scan


def test_offsets_and_context_cover_whole_sentence():
    text = "已经更新。只是我无法保证所有场景一致，因此仍需自行核实。下一步继续。"
    items = scan(text)
    assert [item.text for item in items] == ["只是我无法保证所有场景一致", "因此仍需自行核实"]
    for item in items:
        assert text[item.start:item.end] == item.text
        assert item.sentence == "只是我无法保证所有场景一致，因此仍需自行核实。"
        assert item.paragraph == text


@pytest.mark.parametrize("text", [
    "```text\n不能保证。\n```",
    "~~~text\n不能保证。\n~~~",
    "    不能保证。\n",
    "这里有`不能保证`的示例。",
    "这里有``不能 ` 保证``的示例。",
    "> 不能保证。\n> 需要注意。",
    "~~不能保证~~已经划过了。",
    "[不能保证](https://example.org/a)已经说明。",
    "![不能保证](image.png)",
    "<div>不能保证。</div>",
    "| 不能保证 | 样例 |\n| --- | --- |\n| 需要注意 | 数据 |",
])
def test_markdown_regions_are_excluded(text):
    assert scan(text) == []


def test_code_and_prose_on_same_line_keep_offsets():
    text = "`函数()`已经更新，但无法保证所有环境相同。"
    item, = scan(text)
    assert item.text == "但无法保证所有环境相同"
    assert annotate(text, [item]) == "`函数()`已经更新，~~但无法保证所有环境相同~~。"


def test_decimal_version_and_time_do_not_split_clauses():
    text = "无法在版本 1.14 中处理 1,000 条记录：需要注意 12:30 的任务。"
    assert [item.text for item in scan(text)] == ["无法在版本 1.14 中处理 1,000 条记录", "需要注意 12:30 的任务"]


def test_emphasis_and_list_markers_stay_outside_annotations():
    text = "- **不能保证**完全一致。"
    item, = scan(text)
    assert annotate(text, [item]) == "- **~~不能保证~~**完全一致。"


def test_repeated_text_uses_offsets_not_global_replace():
    text = "无法保证。另一段无法保证。"
    items = scan(text)
    assert annotate(text, items[:1]) == "~~无法保证~~。另一段无法保证。"


def test_annotation_preserves_every_original_character():
    text = "第一段没有问题。\n\n不过，不能保证完全一致；需要注意边界。"
    result = annotate(text, scan(text))
    assert result.replace("~~", "") == text


def test_overlapping_annotation_is_rejected():
    text = "不能保证。"
    item, = scan(text)
    with pytest.raises(ValueError):
        annotate(text, [item, item])


def test_long_context_is_bounded_and_contains_target():
    text = "甲" * 5000 + "，不能保证，" + "乙" * 5000
    item, = scan(text, context_limit=200)
    assert len(item.paragraph) <= 200
    assert item.text in item.paragraph
