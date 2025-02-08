# 使用官方 Python 镜像
FROM python:3.10-alpine

# 安装系统依赖（新增 zip）
RUN apk add --no-cache yq jq curl unzip zip gettext

# 安装 k6
RUN curl -L https://github.com/grafana/k6/releases/download/v0.48.0/k6-v0.48.0-linux-amd64.tar.gz \
    | tar xz && mv k6-v0.48.0-linux-amd64/k6 /usr/local/bin/k6

# 设置工作目录
WORKDIR /app

# 复制文件（排除结果目录）
COPY . .

# 声明卷（用于挂载结果）
VOLUME /app/result

# 安装 Python 依赖
RUN pip install -r requirements.txt

# 设置默认环境变量
ENV DEFAULT_DURATION="30s" \
    DEFAULT_VUS="300" \
    HTTP_TIMEOUT="15s" \
    BCS_API_URL="http://bcs-api.bkdomain/bcsapi/v4" \
    BCS_TOKEN="xxxx" \
    CLUSTER_ID="BCS-K8S-00000" \
    PROJECT_CODE="blueking" \
    BKREPO_URL="http://bkrepo.bkdomain/generic/blueking/bcs-test" \
    BKREPO_USERNAME="admin" \
    BKREPO_PASSWORD="xxxxx"

# 确保脚本可执行
RUN chmod +x /app/start.sh

# 运行入口启动脚本
CMD ["/app/start.sh"]
