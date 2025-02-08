import json
import math
from datetime import datetime

def format_bytes(num_bytes):
    if num_bytes == 0:
        return "0 B"
    k = 1024
    sizes = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(num_bytes, k)))
    return f"{num_bytes / (k ** i):.2f} {sizes[i]}"

def save_results_to_html(final_results, file_path, global_config, global_vars, test_start, test_end, pre_count, post_count, k6_version):
    # 计算总请求数和失败请求数
    total_requests = sum(int(result['totalRequests']) for result in final_results)
    total_failures = sum(int(result['failCount']) for result in final_results)
    
    summary_boxes = f"""
    <div class="row">
      <div class="box">
        <i class="fas fa-globe icon"></i>
        <h4>Total Requests</h4>
        <div class="bignum">{total_requests}</div>
      </div>
      
      <div class="box {'failed' if total_failures > 0 else ''}">
        <i class="far fa-times-circle icon"></i>
        <h4>Failed Requests</h4>
        <div class="bignum">{total_failures}</div>
      </div>
      
      <div class="box metricbox">
        <i class="fas fa-clock icon"></i>
        <h4>Test Duration</h4>
        <div class="bignum">{str(test_end - test_start).split('.')[0]}</div>
      </div>
    </div>
    """

    # 创建测试概要选项卡内容
    summary_tab = f"""
    <div class="tab">
      <h2>Test Summary</h2>
      <table class="pure-table pure-table-striped">
        <tr><td><b>Start Time</b></td><td>{test_start.strftime("%Y-%m-%d %H:%M:%S")}</td></tr>
        <tr><td><b>End Time</b></td><td>{test_end.strftime("%Y-%m-%d %H:%M:%S")}</td></tr>
        <tr><td><b>Base URL</b></td><td>{global_config.get("base_url", "")}</td></tr>
        <tr><td><b>Default VUs</b></td><td>{global_config.get("defaultVUs", "")}</td></tr>
        <tr><td><b>HTTP Timeout</b></td><td>{global_config.get("http_timeout", "")}</td></tr>
        <tr><td><b>Pre Requests</b></td><td>{pre_count}</td></tr>
        <tr><td><b>Test Endpoints</b></td><td>{len(final_results)}</td></tr>
        <tr><td><b>Post Requests</b></td><td>{post_count}</td></tr>
        <tr><td><b>K6 Version</b></td><td>{k6_version}</td></tr>
      </table>
    </div>
    """

    # 创建详细结果选项卡内容
    results_tab = """<div class="tab">
      <h2>Detailed Results</h2>
      <table class="pure-table pure-table-striped">
        <thead>
          <tr>
    """
    
    keys = list(final_results[0].keys()) if final_results else []
    for key in keys:
        results_tab += f"<th>{key}</th>"
    results_tab += "</tr></thead><tbody>"
    
    for result in final_results:
        results_tab += "<tr>"
        for key in keys:
            cell_value = result.get(key, '')
            if key == "endpointName":
                html_file = f"k6-summary-{cell_value}.html"
                cell_value = f'<a href="{html_file}" target="_blank">{cell_value}</a>'
            results_tab += f"<td>{cell_value}</td>"
        results_tab += "</tr>"
    results_tab += "</tbody></table></div>"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>K6 Load Test Summary: {test_start.strftime("%Y-%m-%d %H:%M")}</title>
    <link rel="stylesheet" href="https://unpkg.com/purecss@2.0.3/build/pure-min.css">
    <link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.15.2/css/all.css">
    <style>
        body {{ margin: 1rem; font-family: Arial, sans-serif; }}
        .row {{ display: flex; flex-wrap: wrap; }}
        .box {{
            flex: 1;
            border-radius: 0.3rem;
            background-color: #3abe3a;
            margin: 1rem;
            padding: 1rem;
            color: white;
            position: relative;
            min-width: 200px;
            box-shadow: 0px 4px 7px -1px rgba(0,0,0,0.49);
        }}
        .failed {{ background-color: #ff6666 !important; }}
        .metricbox {{ background-color: #5697e2; }}
        .box h4 {{
            margin: 0;
            padding-bottom: 0.5rem;
            text-align: center;
            font-size: 1.1rem;
        }}
        .bignum {{
            text-align: center;
            font-size: 2rem;
            font-weight: bold;
        }}
        .icon {{
            position: absolute;
            top: 60%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: rgba(255,255,255,0.2);
            font-size: 4rem;
            z-index: 0;
        }}
        .tabs {{
            margin-top: 2rem;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .tab-buttons {{
            background: #f8f8f8;
            border-bottom: 1px solid #ddd;
            padding: 0.5rem;
        }}
        .tab-buttons button {{
            border: none;
            background: none;
            padding: 0.5rem 1rem;
            margin-right: 0.5rem;
            cursor: pointer;
            font-size: 1rem;
        }}
        .tab-buttons button.active {{
            border-bottom: 2px solid #4a90e2;
            color: #4a90e2;
        }}
        .tab {{ padding: 1rem; }}
        table {{ margin: 1rem 0; width: 100%; }}
        th {{ background: #f2f2f2; }}
        td, th {{ padding: 0.5rem; text-align: left; }}
        a {{ color: #4a90e2; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>
        <i class="fas fa-chart-line"></i>
        K6 Load Test Summary: {test_start.strftime("%Y-%m-%d %H:%M")}
    </h1>
    
    {summary_boxes}
    
    <div class="tabs">
        <div class="tab-buttons">
            <button onclick="openTab('summary')" class="active">Summary</button>
            <button onclick="openTab('results')">Detailed Results</button>
        </div>
        
        <div id="summary" class="tab-content">
            {summary_tab}
        </div>
        
        <div id="results" class="tab-content" style="display:none">
            {results_tab}
        </div>
    </div>

    <script>
    function openTab(tabName) {{
        var i, tabContent, tabButtons;
        tabContent = document.getElementsByClassName("tab-content");
        for (i = 0; i < tabContent.length; i++) {{
            tabContent[i].style.display = "none";
        }}
        tabButtons = document.getElementsByClassName("tab-buttons")[0].getElementsByTagName("button");
        for (i = 0; i < tabButtons.length; i++) {{
            tabButtons[i].className = tabButtons[i].className.replace(" active", "");
        }}
        document.getElementById(tabName).style.display = "block";
        event.currentTarget.className += " active";
    }}
    </script>
</body>
</html>"""

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"测试结果已保存到 HTML 文件：{file_path}")