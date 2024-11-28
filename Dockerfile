FROM ollama/ollama

# 设置工作目录
WORKDIR /root/.ollama

# 暴露 Ollama 默认端口
EXPOSE 11434

# 启动 Ollama 服务
CMD ["ollama", "serve", "--port", "${PORT}"]
