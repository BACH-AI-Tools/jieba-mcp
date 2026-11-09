# jieba-mcp

<!-- mcp-name: io.github.BACH-AI-Tools/jieba -->

**English** | [简体中文](README.zh-CN.md)

Chinese text processing for any MCP client: word segmentation, keyword extraction, part-of-speech tagging, a user dictionary and Simplified/Traditional conversion. It is built on [jieba](https://github.com/fxsjy/jieba) and runs locally over stdio with a single `uvx jieba-mcp`.

LLMs can read Chinese, but they cannot reliably count, split or rank Chinese words. These tools give them deterministic answers that are the same on every run.

## Tools

| Tool | What it does |
|---|---|
| `segment` | Split text into words. Modes: `precise` (default), `full`, `search` |
| `extract_keywords` | Top keywords by `tfidf` (default) or `textrank`, with optional weights and POS filter |
| `pos_tag` | Words plus part-of-speech tags (`n`, `v`, `ns`, `nr`, …) |
| `add_user_words` | Add domain words (names, jargon, brands) so later calls keep them whole |
| `convert_chinese` | Simplified ⇄ Traditional via OpenCC configs (`s2t`, `t2s`, `s2tw`, `tw2s`, `s2twp`, `tw2sp`, `s2hk`, `hk2s`) |

Every tool returns structured JSON (`structuredContent`) and declares an output schema. Parameters are described in each tool's JSON Schema, so clients can show them.

## Install

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
uvx jieba-mcp            # runs the server on stdio
```

Until the package is on PyPI, run it from GitHub instead: `uvx --from git+https://github.com/BACH-AI-Tools/jieba-mcp jieba-mcp`.

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "jieba": {
      "command": "uvx",
      "args": ["jieba-mcp"]
    }
  }
}
```

### Cursor

Add the same block to `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (per project).

### Claude Code

```bash
claude mcp add jieba -- uvx jieba-mcp
```

### HTTP transports (optional)

```bash
jieba-mcp --transport streamable-http --port 9998   # http://127.0.0.1:9998/mcp
jieba-mcp --transport sse --port 9998               # http://127.0.0.1:9998/sse
```

`--host` defaults to `127.0.0.1`. The Docker image serves SSE on `0.0.0.0:9998`:

```bash
docker build -t jieba-mcp . && docker run -p 9998:9998 jieba-mcp
```

## Examples

The outputs below are real `structuredContent` returned over stdio by version 1.0.0. The first call takes about a second while jieba loads its dictionary.

### `segment`

```json
{"text": "我来到北京清华大学"}
→ {"mode": "precise", "tokens": ["我", "来到", "北京", "清华大学"], "count": 4}

{"text": "我来到北京清华大学", "mode": "full"}
→ {"mode": "full", "tokens": ["我", "来到", "北京", "清华", "清华大学", "华大", "大学"], "count": 7}

{"text": "小明硕士毕业于中国科学院计算所", "mode": "search"}
→ {"mode": "search", "tokens": ["小明", "硕士", "毕业", "于", "中国", "科学", "学院", "科学院", "中国科学院", "计算", "计算所"], "count": 11}
```

Set `"hmm": false` to turn off jieba's HMM model, which joins unknown words.

### `extract_keywords`

```json
{"text": "我来到北京清华大学，清华大学是一所综合性大学", "top_k": 3}
→ {"method": "tfidf", "keywords": [
     {"word": "清华大学", "weight": 2.308741},
     {"word": "一所", "weight": 1.115948},
     {"word": "综合性", "weight": 1.044143}]}

{"text": "线程是程序执行中一个单一的顺序控制流程，进程内有一个或多个线程，线程共享进程的资源",
 "top_k": 3, "method": "textrank"}
→ {"method": "textrank", "keywords": [
     {"word": "线程", "weight": 1.0},
     {"word": "进程", "weight": 0.7957},
     {"word": "共享", "weight": 0.504354}]}
```

Options:
- `with_weight: false` returns words only, and each `weight` is `null`.
- `allow_pos` keeps only the listed tags. For example, `["ns"]` keeps only place names.
- TextRank defaults to `["ns", "n", "vn", "v"]`.

### `pos_tag`

```json
{"text": "我爱北京天安门"}
→ {"tokens": [{"word": "我", "flag": "r"}, {"word": "爱", "flag": "v"},
              {"word": "北京", "flag": "ns"}, {"word": "天安门", "flag": "ns"}], "count": 4}
```

Tags follow jieba's ICTCLAS-compatible set; see the [jieba README](https://github.com/fxsjy/jieba).

### `add_user_words`

```json
segment {"text": "大语言模型正在改变检索增强生成"}
→ {"tokens": ["大", "语言", "模型", "正在", "改变", "检索", "增强", "生成"], ...}

add_user_words {"words": [{"word": "大语言模型", "tag": "nz"}, {"word": "检索增强生成"}]}
→ {"added": ["大语言模型", "检索增强生成"], "count": 2}

segment {"text": "大语言模型正在改变检索增强生成"}
→ {"tokens": ["大语言模型", "正在", "改变", "检索增强生成"], ...}

pos_tag {"text": "大语言模型正在改变检索增强生成"}
→ {"tokens": [{"word": "大语言模型", "flag": "nz"}, {"word": "正在", "flag": "t"},
              {"word": "改变", "flag": "v"}, {"word": "检索增强生成", "flag": "x"}], ...}
```

- **Where the words live:** in the server process's memory only. They apply to all later calls and to every client of that process. They are lost when the process restarts, and nothing is written to disk.
- **Tags:** give a `tag` if you want `pos_tag` to label the word; words added without one are tagged `x`.
- **Frequency:** `freq` is optional. If you omit it, jieba picks one that keeps the word whole.

### `convert_chinese`

```json
{"text": "软件和鼠标", "config": "s2twp"}  → {"config": "s2twp", "text": "軟體和滑鼠"}
{"text": "漢字轉換", "config": "t2s"}      → {"config": "t2s", "text": "汉字转换"}
```

## Development

```bash
git clone https://github.com/BACH-AI-Tools/jieba-mcp.git
cd jieba-mcp
pip install -e '.[test]'
pytest                       # tool tests + a real stdio session via the MCP client
```

## License and acknowledgements

- MIT, see [LICENSE](LICENSE).
- [jieba](https://github.com/fxsjy/jieba) by Sun Junyi (fxsjy), MIT License. It does all of the segmentation, tagging and keyword work.
- [opencc-python-reimplemented](https://github.com/yichen0831/opencc-python), Apache-2.0. It is a pure-Python port of [OpenCC](https://github.com/BYVoid/OpenCC) and provides `convert_chinese`.
- The [Model Context Protocol](https://modelcontextprotocol.io/) Python SDK.
