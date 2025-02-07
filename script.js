// script.js

import http from "k6/http";
import { check } from "k6";
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
  // 这里 data 是 k6 的测试结果对象，包含指标
  let filename = __ENV.REPORT_NAME || `k6-summary-${Date.now()}.json`;

  return {
    // 在控制台打印简要结果
    stdout: textSummary(data, { indent: " ", enableColors: true }),

    // 生成一个 JSON 文件，包含详细指标
    [filename]: JSON.stringify(data, null, 2),
  };
}
