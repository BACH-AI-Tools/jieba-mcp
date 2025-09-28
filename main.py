from typing import Literal, List
from fastmcp import FastMCP
import jieba

APP_NAME = "jieba-mcp"

mcp = FastMCP(APP_NAME, version="0.1.0", host="0.0.0.0", port=9998)

@mcp.tool()
def jieba_segment(
    text: str,
    mode: Literal["precise", "full", "search"] = "precise",
) -> List[str]:
    """
    使用 jieba 对中文文本进行分词。

    参数:
      - text: 待分词文本
      - mode: 分词模式，可选：
          - precise: 精确模式（默认）
          - full: 全模式
          - search: 搜索引擎模式
    返回:
      - 分词后的 token 列表（已去除空白）
    """
    if not text:
        return []

    if mode == "full":
        seg_iter = jieba.cut(text, cut_all=True)
    elif mode == "search":
        seg_iter = jieba.cut_for_search(text)
    else:  # precise
        seg_iter = jieba.cut(text, cut_all=False)

    return [tok.strip() for tok in seg_iter if tok and tok.strip()]


if __name__ == "__main__":
    mcp.run(transport="sse")