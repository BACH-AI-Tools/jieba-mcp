# jieba-mcp

基于 jieba 中文分词的 MCP (Model Context Protocol) 服务器，使用 FastMCP 框架构建。

## 项目简介

这是一个 MCP 服务器，提供中文文本分词功能。通过 FastMCP 框架将 jieba 分词能力封装为标准的 MCP 工具，可以被支持 MCP 协议的客户端（如 Claude Desktop）调用。

## 功能特性

- 支持三种分词模式：
  - **精确模式**（默认）：试图将句子最精确地切开，适合文本分析
  - **全模式**：把句子中所有的可以成词的词语都扫描出来
  - **搜索引擎模式**：在精确模式的基础上，对长词再次切分，提高召回率
- 自动过滤空白字符
- 基于 SSE (Server-Sent Events) 传输协议
- Docker 容器化部署支持

## 安装和使用

### 1. 直接运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务器
python main.py
```

### 2. Docker 部署

```bash
# 构建镜像
docker build -t jieba-mcp .

# 运行容器
docker run -p 9998:9998 jieba-mcp
```

## API 文档

### jieba_segment 工具

对中文文本进行分词处理。

**参数：**
- `text` (str): 待分词的中文文本
- `mode` (str, 可选): 分词模式，默认为 "precise"
  - `"precise"`: 精确模式
  - `"full"`: 全模式
  - `"search"`: 搜索引擎模式

**返回值：**
- `List[str]`: 分词后的词语列表（已去除空白字符）

**示例：**
```python
# 精确模式
jieba_segment("我来到北京清华大学")
# 返回: ["我", "来到", "北京", "清华大学"]

# 全模式
jieba_segment("我来到北京清华大学", mode="full")
# 返回: ["我", "来到", "北京", "清华", "清华大学", "华大", "大学"]

# 搜索引擎模式
jieba_segment("小明硕士毕业于中国科学院计算所", mode="search")
# 返回: ["小明", "硕士", "毕业", "于", "中国", "科学", "学院", "科学院", "中国科学院", "计算", "计算所"]
```

## 项目结构

```
jieba-mcp/
├── main.py              # 主程序文件
├── requirements.txt     # Python 依赖包
├── Dockerfile          # Docker 构建文件
└── README.md           # 项目说明文档
```

## 技术栈

- **Python 3.11+**: 主要编程语言
- **jieba**: 中文分词库
- **FastMCP**: MCP 服务器框架
- **Docker**: 容器化部署

## 配置

服务器默认配置：
- **主机**: `0.0.0.0`
- **端口**: `9998`
- **传输协议**: SSE (Server-Sent Events)

如需修改配置，请编辑 [`main.py`](main.py) 文件中的相关参数。

## 开发

### 本地开发环境搭建

1. 克隆项目：
```bash
git clone <repository-url>
cd jieba-mcp
```

2. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 启动开发服务器：
```bash
python main.py
```

### MCP 客户端集成

要在支持 MCP 的客户端（如 Claude Desktop）中使用此服务器：

1. 启动 jieba-mcp 服务器
2. 在客户端配置中添加 MCP 服务器连接
3. 指定服务器地址为 `http://localhost:9998`

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。

## 许可证

本项目采用 MIT 许可证。详情请参阅 LICENSE 文件。

## 相关链接

- [jieba](https://github.com/fxsjy/jieba) - 中文分词库
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP 服务器框架
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP 协议规范