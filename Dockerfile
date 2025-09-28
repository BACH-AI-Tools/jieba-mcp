FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

# 拷贝源码
COPY . .

# 安装依赖：
# - 若有 requirements.txt 按其安装
# - 否则对当前项目做可编辑安装（需要 pyproject.toml/setup.*）
RUN if [ -f "requirements.txt" ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir -e .; \
    fi

EXPOSE 9998
CMD ["python", "main.py"]