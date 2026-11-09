"""MCP server exposing jieba segmentation, keyword extraction and POS tagging."""

from __future__ import annotations

import argparse
import logging
from typing import Annotated, Literal

import jieba
import jieba.analyse
import jieba.posseg
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from opencc import OpenCC
from pydantic import BaseModel, Field

from jieba_mcp import __version__

# jieba logs "Building prefix dict ..." at DEBUG/INFO level on first use.
jieba.setLogLevel(logging.WARNING)

mcp = FastMCP(
    "jieba",
    instructions=(
        "Chinese text processing with jieba: word segmentation, keyword "
        "extraction (TF-IDF / TextRank), part-of-speech tagging, an "
        "in-memory user dictionary, and Simplified/Traditional conversion."
    ),
    website_url="https://github.com/BACH-AI-Tools/jieba-mcp",
)
# FastMCP has no version argument; without this, initialize reports the
# installed mcp SDK version as the server version.
mcp._mcp_server.version = __version__

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)

Text = Annotated[str, Field(description="Chinese text to process.")]
Hmm = Annotated[
    bool,
    Field(description="Use the HMM model to discover words not in the dictionary."),
]


# --------------------------------------------------------------------------
# Result models (exposed to clients as the tools' output schemas)
# --------------------------------------------------------------------------


class SegmentResult(BaseModel):
    mode: Literal["precise", "full", "search"] = Field(description="Mode used.")
    tokens: list[str] = Field(description="Tokens in order, whitespace removed.")
    count: int = Field(description="Number of tokens.")


class Keyword(BaseModel):
    word: str
    weight: float | None = Field(
        default=None, description="Score; null when with_weight is false."
    )


class KeywordResult(BaseModel):
    method: Literal["tfidf", "textrank"]
    keywords: list[Keyword] = Field(description="Keywords, highest score first.")


class TaggedToken(BaseModel):
    word: str
    flag: str = Field(description="ICTCLAS-style part-of-speech tag, e.g. n, v, nr.")


class PosTagResult(BaseModel):
    tokens: list[TaggedToken]
    count: int


class UserWord(BaseModel):
    word: str = Field(description="The word to add, e.g. 石墨烯.")
    freq: int | None = Field(
        default=None,
        ge=1,
        description="Word frequency; omit to let jieba pick one that keeps the word whole.",
    )
    tag: str | None = Field(default=None, description="Optional POS tag, e.g. n or nz.")


class AddWordsResult(BaseModel):
    added: list[str] = Field(description="Words added to the in-memory dictionary.")
    count: int


ConvertConfig = Literal["s2t", "t2s", "s2tw", "tw2s", "s2twp", "tw2sp", "s2hk", "hk2s"]


class ConvertResult(BaseModel):
    config: ConvertConfig
    text: str = Field(description="Converted text.")


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------


@mcp.tool(title="Segment Chinese text", annotations=READ_ONLY)
def segment(
    text: Text,
    mode: Annotated[
        Literal["precise", "full", "search"],
        Field(
            description=(
                "precise: the most likely single segmentation (default, best "
                "for analysis); full: every dictionary word that can be "
                "formed, overlapping; search: precise mode plus sub-words of "
                "long words, for search indexing."
            )
        ),
    ] = "precise",
    hmm: Hmm = True,
) -> SegmentResult:
    """Split Chinese text into words with jieba."""
    if mode == "full":
        pieces = jieba.cut(text, cut_all=True)
    elif mode == "search":
        pieces = jieba.cut_for_search(text, HMM=hmm)
    else:
        pieces = jieba.cut(text, cut_all=False, HMM=hmm)
    tokens = [p.strip() for p in pieces if p and p.strip()]
    return SegmentResult(mode=mode, tokens=tokens, count=len(tokens))


@mcp.tool(title="Extract keywords", annotations=READ_ONLY)
def extract_keywords(
    text: Text,
    top_k: Annotated[
        int, Field(ge=1, le=200, description="Maximum number of keywords.")
    ] = 10,
    method: Annotated[
        Literal["tfidf", "textrank"],
        Field(
            description=(
                "tfidf: rank by TF-IDF against jieba's built-in IDF table; "
                "textrank: graph-based ranking of co-occurring words."
            )
        ),
    ] = "tfidf",
    with_weight: Annotated[
        bool, Field(description="Include each keyword's score.")
    ] = True,
    allow_pos: Annotated[
        list[str] | None,
        Field(
            description=(
                'Only keep words with these POS tags, e.g. ["n", "ns", '
                '"vn"]. Default: no filter for tfidf, '
                '["ns", "n", "vn", "v"] for textrank.'
            )
        ),
    ] = None,
) -> KeywordResult:
    """Extract the most important keywords from Chinese text."""
    if method == "textrank":
        pos = tuple(allow_pos) if allow_pos else ("ns", "n", "vn", "v")
        found = jieba.analyse.textrank(
            text, topK=top_k, withWeight=with_weight, allowPOS=pos
        )
    else:
        pos = tuple(allow_pos) if allow_pos else ()
        found = jieba.analyse.extract_tags(
            text, topK=top_k, withWeight=with_weight, allowPOS=pos
        )
    if with_weight:
        keywords = [Keyword(word=w, weight=round(s, 6)) for w, s in found]
    else:
        keywords = [Keyword(word=w) for w in found]
    return KeywordResult(method=method, keywords=keywords)


@mcp.tool(title="Part-of-speech tagging", annotations=READ_ONLY)
def pos_tag(text: Text, hmm: Hmm = True) -> PosTagResult:
    """Segment Chinese text and tag each word with its part of speech."""
    tokens = [
        TaggedToken(word=p.word, flag=p.flag)
        for p in jieba.posseg.cut(text, HMM=hmm)
        if p.word.strip()
    ]
    return PosTagResult(tokens=tokens, count=len(tokens))


@mcp.tool(
    title="Add words to the user dictionary",
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False, idempotentHint=True
    ),
)
def add_user_words(
    words: Annotated[
        list[UserWord],
        Field(min_length=1, max_length=10000, description="Words to add."),
    ],
) -> AddWordsResult:
    """Add domain words (names, jargon, brands) so later calls keep them whole.

    The dictionary lives in this server process's memory only: it affects
    every later call to segment, pos_tag and extract_keywords, is shared by
    all clients of this process, and is gone after a restart. Nothing is
    written to disk.
    """
    added = []
    for entry in words:
        word = entry.word.strip()
        if not word:
            continue
        jieba.add_word(word, freq=entry.freq, tag=entry.tag)
        added.append(word)
    return AddWordsResult(added=added, count=len(added))


_converters: dict[str, OpenCC] = {}


@mcp.tool(title="Convert Simplified / Traditional Chinese", annotations=READ_ONLY)
def convert_chinese(
    text: Text,
    config: Annotated[
        ConvertConfig,
        Field(
            description=(
                "OpenCC conversion: s2t / t2s (Simplified <-> Traditional), "
                "s2tw / tw2s (Taiwan standard), s2twp / tw2sp (Taiwan, with "
                "phrases such as 软件 <-> 軟體), s2hk / hk2s (Hong Kong)."
            )
        ),
    ] = "s2t",
) -> ConvertResult:
    """Convert between Simplified and Traditional Chinese."""
    converter = _converters.get(config)
    if converter is None:
        converter = _converters[config] = OpenCC(config)
    return ConvertResult(config=config, text=converter.convert(text))


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="jieba-mcp", description="Chinese text processing MCP server (jieba)."
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport (default: stdio).",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Bind address for sse / streamable-http."
    )
    parser.add_argument(
        "--port", type=int, default=9998, help="Port for sse / streamable-http."
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    args = parser.parse_args(argv)

    if args.transport != "stdio":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        # Same rule the SDK applies when FastMCP is constructed with a host:
        # DNS-rebinding protection (Host header must be localhost) only makes
        # sense for loopback binds.
        if args.host not in ("127.0.0.1", "localhost", "::1") and hasattr(
            mcp.settings, "transport_security"
        ):
            mcp.settings.transport_security = None
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
