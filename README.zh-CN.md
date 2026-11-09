# jieba-mcp

[English](README.md) | **简体中文**

给任何 MCP 客户端用的中文文本处理工具，基于 [jieba](https://github.com/fxsjy/jieba)：分词、关键词提取、词性标注、自定义词典、繁简转换。本地以 stdio 运行，一条 `uvx jieba-mcp` 就能启动。

大模型读得懂中文，但不擅长稳定地切词、数词、给词排序。这些工具每次都给出确定、可复现的结果。

## 工具一览

| 工具 | 作用 |
|---|---|
| `segment` | 分词。模式：`precise` 精确（默认）、`full` 全模式、`search` 搜索引擎模式 |
| `extract_keywords` | 关键词提取：`tfidf`（默认）或 `textrank`，可返回权重、按词性过滤 |
| `pos_tag` | 分词并标注词性（`n`、`v`、`ns`、`nr` 等） |
| `add_user_words` | 加入领域词（人名、术语、品牌），之后的调用不再把它切开 |
| `convert_chinese` | 繁简转换，使用 OpenCC 配置：`s2t`、`t2s`、`s2tw`、`tw2s`、`s2twp`、`tw2sp`、`s2hk`、`hk2s` |

每个工具都返回结构化 JSON（`structuredContent`）并声明输出 schema；参数的含义都写在 JSON Schema 里。

## 安装

需要 Python 3.10+ 和 [uv](https://docs.astral.sh/uv/)。

```bash
uvx jieba-mcp            # 以 stdio 方式启动
```

还没发布到 PyPI 之前，可以直接从 GitHub 运行：`uvx --from git+https://github.com/BACH-AI-Tools/jieba-mcp jieba-mcp`。

### Claude Desktop

在 `claude_desktop_config.json` 中加入：

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

把同样的配置写进 `~/.cursor/mcp.json`（全局）或 `.cursor/mcp.json`（单个项目）。

### Claude Code

```bash
claude mcp add jieba -- uvx jieba-mcp
```

### HTTP 传输（可选）

```bash
jieba-mcp --transport streamable-http --port 9998   # http://127.0.0.1:9998/mcp
jieba-mcp --transport sse --port 9998               # http://127.0.0.1:9998/sse
```

`--host` 默认是 `127.0.0.1`。Docker 镜像在 `0.0.0.0:9998` 上提供 SSE：

```bash
docker build -t jieba-mcp . && docker run -p 9998:9998 jieba-mcp
```

## 调用示例

下面都是 1.0.0 版本通过 stdio 实际返回的 `structuredContent`。第一次调用要加载词典，约需 1 秒。

### `segment`

```json
{"text": "我来到北京清华大学"}
→ {"mode": "precise", "tokens": ["我", "来到", "北京", "清华大学"], "count": 4}

{"text": "我来到北京清华大学", "mode": "full"}
→ {"mode": "full", "tokens": ["我", "来到", "北京", "清华", "清华大学", "华大", "大学"], "count": 7}

{"text": "小明硕士毕业于中国科学院计算所", "mode": "search"}
→ {"mode": "search", "tokens": ["小明", "硕士", "毕业", "于", "中国", "科学", "学院", "科学院", "中国科学院", "计算", "计算所"], "count": 11}
```

传 `"hmm": false` 可以关闭 jieba 的 HMM 新词发现。

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

可选参数：
- `with_weight: false`：只返回词，每个 `weight` 为 `null`。
- `allow_pos`：只保留指定词性，例如 `["ns"]` 只保留地名。
- TextRank 默认的词性过滤是 `["ns", "n", "vn", "v"]`。

### `pos_tag`

```json
{"text": "我爱北京天安门"}
→ {"tokens": [{"word": "我", "flag": "r"}, {"word": "爱", "flag": "v"},
              {"word": "北京", "flag": "ns"}, {"word": "天安门", "flag": "ns"}], "count": 4}
```

词性标记与 jieba 一致（兼容 ICTCLAS），详见 [jieba README](https://github.com/fxsjy/jieba)。

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

- **词存在哪里**：只在服务进程的内存里。加入后对之后的所有调用、对连到这个进程的所有客户端都生效；进程重启后失效，不会写任何文件。
- **词性**：想让 `pos_tag` 标出词性，就要传 `tag`；不传的词会被标成 `x`。
- **词频**：`freq` 可以不传，jieba 会自动选一个能让这个词不被切开的词频。

### `convert_chinese`

```json
{"text": "软件和鼠标", "config": "s2twp"}  → {"config": "s2twp", "text": "軟體和滑鼠"}
{"text": "漢字轉換", "config": "t2s"}      → {"config": "t2s", "text": "汉字转换"}
```

## 开发

```bash
git clone https://github.com/BACH-AI-Tools/jieba-mcp.git
cd jieba-mcp
pip install -e '.[test]'
pytest                       # 工具测试 + 用 MCP 客户端跑一次真实的 stdio 会话
```

## 许可与致谢

- 本项目采用 MIT 许可，见 [LICENSE](LICENSE)。
- [jieba](https://github.com/fxsjy/jieba)：作者 Sun Junyi（fxsjy），MIT 许可。分词、词性标注和关键词提取全部由它完成。
- [opencc-python-reimplemented](https://github.com/yichen0831/opencc-python)：Apache-2.0 许可，是 [OpenCC](https://github.com/BYVoid/OpenCC) 的纯 Python 实现，提供繁简转换。
- [Model Context Protocol](https://modelcontextprotocol.io/) 官方 Python SDK。
