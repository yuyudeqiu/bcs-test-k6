.PHONY: run build init help clean

help:
	@echo "Usage:"
	@echo "  make run    - 运行压测"
	@echo "  make build  - 构建Docker镜像"
	@echo "  make init   - 初始化配置文件"
	@echo "  make clean  - 清理压测结果和临时文件"
	@echo "  make help   - 显示帮助信息"

run:
	python3 controller.py

build:
	docker build -t bcs-test-k6 .

init:
	@if [ ! -f config.yaml ]; then \
		envsubst < config.yaml.tmpl > config.yaml && \
		echo "配置文件 config.yaml 已生成。您可以直接编辑该文件或通过设置环境变量来自定义配置。"; \
	else \
		echo "检测到配置文件 config.yaml 已存在，初始化步骤已跳过。"; \
	fi
	@pip install -r requirements.txt
	@echo "Python 依赖已成功安装。"

clean:
	@rm -rf results
	@rm -f *.zip
	@echo "已清理压测结果和临时文件"
