#!/bin/sh

echo "开始渲染配置文件..."
envsubst < config.yaml.tmpl > config.yaml

echo "开始执行压测..."
python3 controller.py