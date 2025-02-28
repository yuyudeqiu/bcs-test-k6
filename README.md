# BCS 压测(K6)

该仓库包含了一个基于 Python 和 K6 的压测项目，用于对指定的 API 接口进行压力测试，并生成测试报告。

## 项目结构

### 主要文件和目录说明
- `charts/`
  - `templates/`
    - `configmap.yaml`: 定义了 Kubernetes 的 ConfigMap，用于存储压测的配置信息。配置信息会从 `values.yaml` 中获取，并通过模板语法进行替换。
  - `values.yaml`: 包含镜像配置、应用内部配置（如全局配置、前置请求、后置请求、压测接口配置等）以及资源配置。
- `controller.py`: 主 Python 脚本，包含了整个压测流程的控制逻辑，如加载配置、执行前置请求、运行 K6 压测、执行后置请求、汇总结果并生成报告、压缩结果文件以及上传压缩文件等功能。

## 配置说明

### `values.yaml` 配置
- **镜像配置**：指定了 Docker 镜像的仓库地址、标签以及拉取策略。
- **应用内部配置**：
  - `global`：全局配置，包括基础 URL、默认持续时间、默认虚拟用户数、HTTP 超时时间、全局令牌以及全局变量等。
  - `bkrepo`：bkrepo 的配置，包括上传的基础 URL、仓库的账号密码。
  - `pre_requests`：前置请求配置，每个请求包含名称、路径、方法以及提取规则等。
  - `post_requests`：后置请求配置，每个请求包含名称、路径、方法以及请求体等。
  - `endpoints`：各接口的压测配置，每个接口包含名称、路径、方法以及请求体等。
- **资源配置**：定义了容器的资源限制和请求。

## 压测流程

### 1. 准备工作
- 检查 `results` 目录是否存在，若不存在则创建。
- 加载 `config.yaml` 配置文件。

### 2. 前置请求
- 执行全局前置请求，并提取需要的变量，更新全局变量。

### 3. K6 压测
- 获取 K6 版本信息。
- 遍历所有压测接口，设置每个接口的虚拟用户数和持续时间，然后运行 K6 进行压测。

### 4. 后置请求
- 若存在后置请求，则执行全局后置请求。

### 5. 结果汇总与报告生成
- 记录测试开始和结束时间，统计前置请求和后置请求的数量。
- 汇总压测结果并生成 HTML 报告，报告包含测试概要信息和压测结果表格。

### 6. 结果打包与上传
- 压缩测试结果文件，生成压缩包。
- 上传压缩包到指定位置。

## 使用方法

### 环境准备
- 确保已经安装 Python 3 和所需的依赖库（如 `yaml`, `json`, `requests`, `subprocess` 等）。
- 确保已经安装 K6 工具。

### 配置修改
- 根据实际情况修改 `charts/values.yaml` 中的配置信息，如镜像配置、应用内部配置和资源配置等。

### 运行压测

#### 本地运行

- 以 `config.yaml.tmpl` 为模板修改配置并且命名为 `config.yaml`
  ```bash
  cp config.yaml.tmpl config.yaml
  ```
- 在项目根目录下执行以下命令：
  ```bash
  python3 controller.py
  ```

#### docker 运行

- 在项目根目录下执行以下命令：
   ```bash
   docker build -t bcs-test-k6 .
   ```

- 运行镜像镜像进行压测

   ```bash
   docker run --rm -v $(pwd)/results:/app/results \
   -e BCS_API_URL="http://bcs-api.bkdomain/bcsapi/v4" \
   -e BCS_TOKEN="xxx" \
   -e BKREPO_PASSWORD="xxx" \
   -e BKREPO_URL="http://bkrepo.bkdomain/generic/xxx/xxx" \
   bcs-test-k6
   ```

## 压测结果

以下提供一个压测结果示例：

[压测结果示例](./example/README.md)