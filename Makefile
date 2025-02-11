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
		echo "配置文件已通过环境变量渲染完成，如需修改请设置对应环境变量或直接编辑 config.yaml"; \
	else \
		echo "配置文件 config.yaml 已存在，跳过初始化"; \
	fi
	@pip install -r requirements.txt
	@echo "Python依赖已安装完成"

clean:
	@rm -rf results
	@rm -f *.zip
	@echo "已清理压测结果和临时文件"
