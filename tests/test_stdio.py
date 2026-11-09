"""End-to-end test: launch the server over stdio with the official MCP client."""

import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from jieba_mcp import __version__

EXPECTED_TOOLS = {
    "segment",
    "extract_keywords",
    "pos_tag",
    "add_user_words",
    "convert_chinese",
}


@pytest.mark.anyio
async def test_stdio_initialize_list_and_call():
    params = StdioServerParameters(command=sys.executable, args=["-m", "jieba_mcp"])
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        init = await session.initialize()
        assert init.serverInfo.name == "jieba"
        assert init.serverInfo.version == __version__

        tools = (await session.list_tools()).tools
        assert {t.name for t in tools} == EXPECTED_TOOLS
        for tool in tools:
            assert tool.description
            assert tool.inputSchema["type"] == "object"
            assert tool.outputSchema is not None

        result = await session.call_tool(
            "segment", {"text": "我来到北京清华大学", "mode": "precise"}
        )
        assert result.isError is False
        assert result.structuredContent == {
            "mode": "precise",
            "tokens": ["我", "来到", "北京", "清华大学"],
            "count": 4,
        }

        bad = await session.call_tool("segment", {"text": "你好", "mode": "nope"})
        assert bad.isError is True
