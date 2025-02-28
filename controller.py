#!/usr/bin/env python3
import os
import sys
import time
import yaml
import json
import subprocess
import requests
import re
import zipfile
import base64
from datetime import datetime
from report_generator import save_results_to_html, format_bytes

# 读取配置文件并返回解析后的对象
def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# 根据类似 "body.data.projectID" 或 "headers.x-new-token" 的规则，从 response 中提取数据
def extract_value(response, rule):
    parts = rule.split(".")
    if not parts:
        return None
    source = parts.pop(0)
    data = None
    if source == "body":
        try:
            data = response.json()
        except Exception as e:
            print("解析 JSON 出错:", e)
            return None
    elif source == "headers":
        data = response.headers
    else:
        return None
    
    for part in parts:
        # 处理数组索引，例如: data[0]
        array_match = re.match(r"(\w+)\[(\d+)\]", part)
        if array_match:
            key, index = array_match.groups()
            if isinstance(data, dict) and key in data:
                array_data = data[key]
                if isinstance(array_data, list) and len(array_data) > int(index):
                    data = array_data[int(index)]
                else:
                    return None
            else:
                return None
        # 处理普通的字典key
        elif isinstance(data, dict) and part in data:
            data = data[part]
        else:
            return None
    return data

# 用于在字符串中替换形如 {xxx} 的占位符，vars_dict 为变量映射
def replace_vars(s, vars_dict):
    if not isinstance(s, str):
        return s
    def repl(match):
        key = match.group(1)
        return str(vars_dict.get(key, match.group(0)))
    return re.sub(r"\{(\w+)\}", repl, s)

# 递归处理对象、列表或字符串中的占位符替换
def replace_vars_in_object(obj, vars_dict):
    if obj is None:
        return obj
    if isinstance(obj, str):
        return replace_vars(obj, vars_dict)
    elif isinstance(obj, list):
        return [replace_vars_in_object(item, vars_dict) for item in obj]
    elif isinstance(obj, dict):
        return { key: replace_vars_in_object(value, vars_dict) for key, value in obj.items() }
    else:
        return obj

def do_pre_requests(pre_requests, global_config, global_vars):
    new_vars = {}
    for pre in pre_requests:
        pre_url = pre.get("url")
        if not pre_url:
            pre_url = global_config.get("base_url", "") + pre.get("path", "")
        pre_url = replace_vars(pre_url, global_vars)
        
        headers = {}
        if global_config.get("global_token"):
            headers["Authorization"] = global_config["global_token"]
        if pre.get("headers"):
            headers.update(pre["headers"])
            headers = replace_vars_in_object(headers, global_vars)
        
        body = pre.get("body")
        if body:
            body = replace_vars_in_object(body, global_vars)
        
        try:
            resp = requests.request(
                method = pre.get("method", "GET"),
                url = pre_url,
                headers = headers,
                json = body,
                timeout = int(str(global_config.get("http_timeout", "5s")).strip("s"))
            )
            resp.raise_for_status()
            
            # 添加调试信息
            print(f"\n调试信息 - 前置请求: {pre.get('name', '')}")
            print("Response 状态码:", resp.status_code)            
            if "extract" in pre:
                for var_name, rule in pre["extract"].items():
                    val = extract_value(resp, rule)
                    print(f"提取变量 {var_name} (规则: {rule}): {val}")
                    if val is None:  # 如果提取变量失败
                        print(f"[ERROR] 前置请求 [{pre.get('name', '')}] 提取变量 {var_name} 失败")
                        return None
                    new_vars[var_name] = val
        except Exception as e:
            print(f"[ERROR] 前置请求 [{pre.get('name', '')}] 失败:", e)
            return None
    return new_vars

def do_post_requests(post_requests, global_config, global_vars):
    for post in post_requests:
        post_url = post.get("url")
        if not post_url:
            post_url = global_config.get("base_url", "") + post.get("path", "")
        post_url = replace_vars(post_url, global_vars)
        
        headers = {}
        if global_config.get("global_token"):
            headers["Authorization"] = global_config["global_token"]
        if post.get("headers"):
            headers.update(post["headers"])
            headers = replace_vars_in_object(headers, global_vars)
        
        final_body = None
        if post.get("body"):
            raw_body = replace_vars_in_object(post["body"], global_vars)
            if isinstance(raw_body, str):
                try:
                    final_body = json.loads(raw_body)
                except Exception as e:
                    print("解析 body JSON 失败，保留原始字符串", e)
                    final_body = raw_body
            else:
                final_body = raw_body
        
        print("\n-------------------------------")
        print(f"调试信息 - 后置请求: {post.get('name', '')}")
        print("URL:", post_url)
        print("Headers:", headers)
        print("Body:", final_body)
        print("-------------------------------")
        
        try:
            resp = requests.request(
                method = post.get("method", "GET"),
                url = post_url,
                headers = headers,
                json = final_body,
                timeout = int(str(global_config.get("http_timeout", "5s")).strip("s"))
            )
            print("Response 状态码:", resp.status_code)
            print("Response 内容:", resp.text)
            resp.raise_for_status()
            print(f"后置请求 [{post.get('name', '')}] 执行成功。")
            if "extract" in post:
                for var_name, rule in post["extract"].items():
                    val = extract_value(resp, rule)
                    global_vars[var_name] = val
        except Exception as e:
            print(f"后置请求 [{post.get('name', '')}] 失败:", e)

def run_k6(ep, global_config, global_vars):
    base_url = global_config.get("base_url", "")
    final_url = ep.get("url") if ep.get("url") else base_url + ep.get("path", "")
    final_url = replace_vars(final_url, global_vars)
    
    final_headers = {}
    if ep.get("headers"):
        final_headers = ep["headers"].copy()
    if "Authorization" not in final_headers and global_config.get("global_token"):
        final_headers["Authorization"] = global_config["global_token"]
    final_headers = replace_vars_in_object(final_headers, global_vars)
    
    final_body = None
    if ep.get("body"):
        final_body = replace_vars_in_object(ep["body"], global_vars)
    
    env = os.environ.copy()
    env.update({
        "TARGET_URL": final_url,
        "METHOD": ep.get("method", "GET"),
        "HEADERS": json.dumps(final_headers),
        "BODY": json.dumps(final_body) if final_body else "",
        "VUS": str(ep.get("vus", global_config.get("defaultVUs", 1))),
        "DURATION": ep.get("duration", global_config.get("defaultDuration", "30s")),
        "REPORT_NAME": f"results/details/k6-summary-{ep.get('name', 'unknown')}.json",
        "TIMEOUT": global_config.get("http_timeout", "5s")
    })
    
    result = subprocess.run(["k6", "run", "script.js"], env=env)
    if result.returncode != 0:
        print(f"接口 [{ep.get('name', '')}] 压测执行失败!")
    else:
        print(f"接口 [{ep.get('name', '')}] 压测完成")

# 修改后的汇总函数，除了汇总表格外传递测试概要参数
def gather_results_and_print_report(endpoints, global_config, global_vars, test_start, test_end, pre_count, post_count, k6_version):
    final_results = []
    total_success = 0
    total_requests = 0
    
    for ep in endpoints:
        summary_file = f"results/details/k6-summary-{ep.get('name', 'unknown')}.json"
        if not os.path.exists(summary_file):
            continue
        with open(summary_file, "r", encoding="utf-8") as f:
            summary_data = json.load(f)
        metrics = summary_data.get("metrics", {})
        state = summary_data.get("state", {})

        total_requests = metrics["http_reqs"]["values"]["count"]
        success_count = metrics["http_req_failed"]["values"]["fails"]
        fail_count = total_requests - success_count
        test_duration_sec = state.get("testRunDurationMs", 30000) / 1000  # 默认 30s
        real_qps = success_count / test_duration_sec if test_duration_sec > 0 else 0

        # 计算单个接口成功率
        success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0
        
        final_results.append({
            "endpointName": ep.get("name", ""),
            "vus": ep.get("vus", global_config.get("defaultVUs", 1)),
            "testDuration": f"{test_duration_sec:.2f}s",
            "qps": f"{real_qps:.2f}",
            "totalRequests": total_requests,
            "successCount": success_count,
            "failCount": fail_count,
            "successRate": f"{success_rate:.2f}%",
            "avgDuration": f"{metrics['http_req_duration']['values']['avg']:.2f}",
            "p90Duration": f"{metrics['http_req_duration']['values']['p(90)']:.2f}",
            "p95Duration": f"{metrics['http_req_duration']['values']['p(95)']:.2f}",
            "maxDuration": f"{metrics['http_req_duration']['values']['max']:.2f}",
            "dataReceived": format_bytes(metrics['data_received']['values']['count']),
            "dataSent": format_bytes(metrics['data_sent']['values']['count']),
            "path": ep.get("path", "N/A")
        })
        
        # 累加总数据
        total_success += success_count
        total_requests += total_requests
    
    # 计算全局成功率
    global_success_rate = (total_success / total_requests * 100) if total_requests > 0 else 0

    print("\n======= 测试汇总结果 =======")
    for result in final_results:
        print(result)
    save_results_to_html(final_results, "results/results.html", global_config, global_vars, test_start, test_end, pre_count, post_count, k6_version)

def compress_results():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"result_{timestamp}.zip"
    try:
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk("results"):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, "results"))
        print(f"\n[INFO] 测试结果已压缩为 {zip_name}")
        return zip_name
    except Exception as e:
        print(f"[ERROR] 压缩失败: {str(e)}")
        return None

def upload_zip_file(zip_file, config):
    bkrepo_config = config.get("bkrepo")
    if not bkrepo_config:
        print("[INFO] 没有配置 bkrepo 信息，跳过上传。")
        return
    base_url = bkrepo_config.get("url")
    username = bkrepo_config.get("username")
    password = bkrepo_config.get("password")
    if not base_url or not username or not password:
        print("[INFO] bkrepo 配置信息不完整，跳过上传。")
        return
    final_url = base_url.rstrip("/") + "/" + os.path.basename(zip_file)
    auth_str = f"{username}:{password}"
    encoded = base64.b64encode(auth_str.encode()).decode()
    headers = {"Authorization": "Basic " + encoded}
    print(f"[INFO] 开始上传压缩包 '{zip_file}' 到 URL: {final_url}")
    try:
        with open(zip_file, "rb") as f:
            response = requests.put(final_url, data=f, headers=headers)
        if 200 <= response.status_code < 300:
            print(f"[INFO] 上传成功：状态码 {response.status_code}。")
            print(f"[INFO] 文件 '{os.path.basename(zip_file)}' 已上传至 {final_url}")
        else:
            print(f"[ERROR] 上传失败：状态码 {response.status_code}。响应内容: {response.text}")
    except Exception as e:
        print(f"[ERROR] 上传异常：{str(e)}")

def main():
    if not os.path.exists("results"):
        os.makedirs("results", exist_ok=True)
    # 确保 details 子目录存在
    details_dir = os.path.join("results", "details")
    if not os.path.exists(details_dir):
        os.makedirs(details_dir, exist_ok=True)
    
    config = load_config()
    global_config = config.get("global", {})
    global_vars = global_config.get("vars", {}).copy() if global_config.get("vars") else {}
    
    # 记录测试开始时间
    test_start = datetime.now()
    
    pre_requests = config.get("pre_requests", [])
    endpoints = config.get("endpoints", [])
    post_requests = config.get("post_requests", [])
    
    print("\n===== 执行全局前置请求... =====\n")
    pre_vars = do_pre_requests(pre_requests, global_config, global_vars)
    if pre_vars is None:  # 前置请求失败
        print("[ERROR] 前置请求失败，程序退出")
        sys.exit(1)
    
    global_vars.update(pre_vars)
    print("前置请求和配置获取到的变量 globalVars =", global_vars)
    
    # 获取 k6 版本信息
    try:
        k6_version = subprocess.run(["k6", "version"], capture_output=True, text=True).stdout.strip()
    except Exception as e:
        k6_version = "unknown"
    
    for ep in endpoints:
        print(f"\n===== 开始压测接口: [{ep.get('name', '')}] =====\n")
        duration = ep.get("duration", global_config.get("defaultDuration", "30s"))
        vus = ep.get("vus", global_config.get("defaultVUs", 1))
        ep["_actualVUs"] = vus
        ep["_actualDuration"] = duration
        
        run_k6(ep, global_config, global_vars)
        print("等待 5 秒后继续...")
        time.sleep(5)
    
    if post_requests:
        print("\n===== 执行全局后置请求... =====\n")
        do_post_requests(post_requests, global_config, global_vars)
    
    # 记录测试结束时间
    test_end = datetime.now()
    pre_count = len(pre_requests)
    post_count = len(post_requests)
    gather_results_and_print_report(endpoints, global_config, global_vars, test_start, test_end, pre_count, post_count, k6_version)
    
    print("\n===== 正在打包测试结果 =====")
    zip_file = compress_results()
    if zip_file:
        print(f"压缩文件路径: {os.path.abspath(zip_file)}")
        upload_zip_file(zip_file, config)

if __name__ == "__main__":
    main()
