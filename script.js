// script.js

import http from "k6/http";
import { check } from "k6";
import { htmlReport } from "https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js";
import { textSummary } from "https://jslib.k6.io/k6-summary/0.0.1/index.js";

// 1. 定义 k6 配置选项
export let options = {
  scenarios: {
    default: {
      executor: "constant-vus",
      vus: __ENV.VUS ? parseInt(__ENV.VUS) : 1,
      duration: __ENV.DURATION || "30s",
      gracefulStop: "0s", // 测试时间到后，不再等待当前迭代完成
    },
  },
};

// 2. 测试逻辑
export default function () {
  // 从环境变量里获取目标信息
  let url = __ENV.TARGET_URL;
  let method = __ENV.METHOD || "GET";

  // 解析请求头
  let headers = {};
  if (__ENV.HEADERS) {
    // HEADERS 是 JSON字符串, 需要 parse
    headers = JSON.parse(__ENV.HEADERS);
  }

  // 解析请求体
  let body = null;
  if (__ENV.BODY) {
    body = JSON.parse(__ENV.BODY);
  }

  // 从环境变量中获取 timeout 参数
  let timeout = __ENV.TIMEOUT || "5s";
  let params = { headers, timeout };

  let res;
  // 发起请求
  if (method.toUpperCase() === "GET") {
    res = http.get(url, params);
  } else {
    res = http.request(method, url, body, params);
  }

  // 在这里进行 check
  check(res, {
    // key: "断言名称"
    // value: 一个回调函数，用于判断是否通过
    "status is 200~299": (r) => r.status >= 200 && r.status < 300,
  });
}

// 3. handleSummary: 测试结束后输出报告
export function handleSummary(data) {
  // 提取基础文件名（去除已有扩展名）
  let baseName = (__ENV.REPORT_NAME || `k6-summary-${Date.now()}`)
    .replace(/\.[^.]+$/, ''); // 删除任何现有扩展名
    
    // 动态生成完整的文件名（避免重复扩展）
    return {
      stdout: textSummary(data, { indent: " ", enableColors: true }),
      
      // 固定扩展名强制为.json
      [`${baseName}.json`]: JSON.stringify(data, null, 2),
      
      // HTML扩展名根据类型自动附加
      [`${baseName}.html`]: htmlReport(data)
    };
}
