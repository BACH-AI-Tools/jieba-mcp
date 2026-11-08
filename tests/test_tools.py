"""Unit tests for the jieba-mcp tools (called directly, no transport)."""

import jieba
import pytest

from jieba_mcp import server


def test_segment_precise_is_default():
    result = server.segment("我来到北京清华大学")
    assert result.mode == "precise"
    assert result.tokens == ["我", "来到", "北京", "清华大学"]
    assert result.count == 4


def test_segment_full_lists_overlapping_words():
    result = server.segment("我来到北京清华大学", mode="full")
    assert result.tokens == ["我", "来到", "北京", "清华", "清华大学", "华大", "大学"]


def test_segment_search_splits_long_words():
    result = server.segment("小明硕士毕业于中国科学院计算所", mode="search")
    assert {"中国", "科学", "学院", "科学院", "中国科学院", "计算所"} <= set(
        result.tokens
    )


def test_segment_drops_whitespace_and_handles_empty_text():
    assert server.segment("  你好 \n 世界 ").tokens == ["你好", "世界"]
    assert server.segment("").tokens == []


def test_segment_hmm_toggle():
    # "杭研" is not in the dictionary; only the HMM model joins it.
    assert "杭研" in server.segment("他来到了网易杭研大厦").tokens
    assert "杭研" not in server.segment("他来到了网易杭研大厦", hmm=False).tokens


def test_extract_keywords_tfidf_with_weights():
    text = "我来到北京清华大学，清华大学是一所综合性大学"
    result = server.extract_keywords(text, top_k=3)
    assert result.method == "tfidf"
    assert result.keywords[0].word == "清华大学"
    assert len(result.keywords) == 3
    weights = [k.weight for k in result.keywords]
    assert all(w > 0 for w in weights)
    assert weights == sorted(weights, reverse=True)


def test_extract_keywords_textrank_without_weights():
    text = "线程是程序执行中一个单一的顺序控制流程，进程内有一个或多个线程，线程共享进程的资源"
    result = server.extract_keywords(
        text, top_k=5, method="textrank", with_weight=False
    )
    assert result.method == "textrank"
    words = [k.word for k in result.keywords]
    assert "线程" in words and "进程" in words
    assert all(k.weight is None for k in result.keywords)


def test_extract_keywords_allow_pos_filters_tags():
    text = "我来到北京清华大学，清华大学是一所综合性大学"
    result = server.extract_keywords(text, top_k=10, allow_pos=["ns"])
    assert [k.word for k in result.keywords] == ["北京"]


def test_pos_tag():
    result = server.pos_tag("我爱北京天安门")
    assert [(t.word, t.flag) for t in result.tokens] == [
        ("我", "r"),
        ("爱", "v"),
        ("北京", "ns"),
        ("天安门", "ns"),
    ]
    assert result.count == 4


@pytest.fixture
def user_word():
    word = "大语言模型"
    yield word
    jieba.del_word(word)


def test_add_user_words_changes_later_segmentation(user_word):
    assert user_word not in server.segment(f"{user_word}发布了").tokens

    result = server.add_user_words(
        [server.UserWord(word=user_word, tag="nz"), server.UserWord(word="  ")]
    )

    assert result.added == [user_word]
    assert result.count == 1
    assert user_word in server.segment(f"{user_word}发布了").tokens
    tagged = {t.word: t.flag for t in server.pos_tag(f"{user_word}发布了").tokens}
    assert tagged[user_word] == "nz"


@pytest.mark.parametrize(
    ("config", "source", "expected"),
    [
        ("s2t", "汉字转换", "漢字轉換"),
        ("t2s", "漢字轉換", "汉字转换"),
        ("s2twp", "软件和鼠标", "軟體和滑鼠"),
    ],
)
def test_convert_chinese(config, source, expected):
    result = server.convert_chinese(source, config=config)
    assert result.config == config
    assert result.text == expected
