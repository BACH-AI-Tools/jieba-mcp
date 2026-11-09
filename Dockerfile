FROM python:3.12-slim

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir .

# The container serves SSE on port 9998, as earlier versions did.
# Use --transport streamable-http for the newer HTTP transport (path /mcp).
EXPOSE 9998
CMD ["jieba-mcp", "--transport", "sse", "--host", "0.0.0.0", "--port", "9998"]
