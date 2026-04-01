"""
Flink 集群画像负载数据采集 + 报告生成一体化脚本

用法：
    python3 scripts/collect_and_report.py

依赖：
    - web/cookie.txt 中有有效的登录 Cookie
    - CDP Proxy 已启动（通过 web-access skill 或手动启动）

流程：
    1. 读取 cookie.txt
    2. 调用 Flink 集群 REST API 采集数据（/overview + /workermanagers/{ip}）
    3. 将原始数据保存到 data/raw/
    4. 调用 gen_report.py 生成 HTML 报告到 output/
"""

import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────────────────────
BASE_URL = (
    "https://mybkcosmos.mybank.cn/proxy/cosmos/flink/cluster/eg168-cluster-pre"
    "/eg168-cluster-pre-service.blink-operator.svc.eg168.mybank.cn:8081"
)
COOKIE_FILE = Path(__file__).parent.parent / "web" / "cookie.txt"
RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
GEN_REPORT_SCRIPT = Path(__file__).parent / "gen_report.py"

WM_IPS = ["33.190.84.129", "33.190.85.106", "33.190.85.70", "33.190.85.103"]
# ─────────────────────────────────────────────────────────────────────────────


def load_cookie() -> str:
    with open(COOKIE_FILE) as f:
        return f.read().strip().splitlines()[0].strip()


def fetch(path: str, cookie: str) -> dict:
    url = BASE_URL + path
    req = urllib.request.Request(url, headers={"Cookie": cookie})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {path}", file=sys.stderr)
        raise
    except urllib.error.URLError as e:
        print(f"  URL error for {path}: {e.reason}", file=sys.stderr)
        raise


def save_json(data: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始采集 eg168-cluster-pre ...")

    # 1. 读取 Cookie
    try:
        cookie = load_cookie()
    except FileNotFoundError:
        print(f"错误：找不到 {COOKIE_FILE}，请先更新 web/cookie.txt", file=sys.stderr)
        sys.exit(1)

    # 2. 采集 overview
    print("  采集 /overview ...")
    overview = fetch("/overview", cookie)
    save_json(overview, RAW_DIR / f"overview_{timestamp}.json")
    # 同时保存为最新快照（供 gen_report.py 使用）
    save_json(overview, RAW_DIR / "overview_latest.json")

    # 3. 采集各 WorkManager 详情
    wm_data = {}
    for ip in WM_IPS:
        print(f"  采集 /workermanagers/{ip} ...")
        try:
            data = fetch(f"/workermanagers/{ip}", cookie)
            save_json(data, RAW_DIR / f"wm_{ip}_{timestamp}.json")
            # 同时保存到 /tmp/ 供 gen_report.py 直接读取（兼容旧路径）
            save_json(data, Path(f"/tmp/wm_{ip}.json"))
            wm_data[ip] = data
        except Exception:
            print(f"  跳过 {ip}（采集失败）")

    print(f"  原始数据已保存到 data/raw/（时间戳：{timestamp}）")

    # 4. 生成报告
    print("  生成 HTML 报告 ...")
    result = subprocess.run(
        [sys.executable, str(GEN_REPORT_SCRIPT)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("报告生成失败：", result.stderr, file=sys.stderr)
        sys.exit(1)

    report_path = OUTPUT_DIR / "cluster_load_report.html"
    print(f"\n完成！报告路径：{report_path}")

    # macOS 自动打开
    if sys.platform == "darwin":
        subprocess.run(["open", str(report_path)])


if __name__ == "__main__":
    main()
