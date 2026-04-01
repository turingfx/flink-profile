"""
Flink 集群画像负载 - 多时间点对比分析报告生成器

用法：
    python3 scripts/gen_timeseries_report.py

输入：
    /tmp/overview_snap{N}.json
    /tmp/wm_{ip}_snap{N}.json

输出：
    output/cluster_load_timeseries_report.html
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

# ── 配置 ──────────────────────────────────────────────────────────────────────
IPS = ["33.190.84.129", "33.190.85.106", "33.190.85.70", "33.190.85.103"]
SNAP_LABELS = {
    "snap1": "T1 (17:26)",
    "snap2": "T2 (17:31)",
}
OUTPUT_PATH = Path(__file__).parent.parent / "output" / "cluster_load_timeseries_report.html"
FLOATING_RATIO_CPU = 1.1
FLOATING_RATIO_MEM = 1.1

# 风险阈值
DEVIATION_WARN = 0.20   # 偏差 > 20% 警告
DEVIATION_CRIT = 0.50   # 偏差 > 50% 严重
LOGICAL_OVERLOAD = 1.0  # 逻辑负载 > 100% 过载


# ── 数据加载 ──────────────────────────────────────────────────────────────────

def load_json(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_snap(snap_id: str) -> dict[str, Any]:
    """加载单个快照的所有数据。"""
    overview = load_json(f"/tmp/overview_{snap_id}.json")
    wms: dict[str, dict] = {}
    for ip in IPS:
        p = Path(f"/tmp/wm_{ip}_{snap_id}.json")
        if p.exists():
            wms[ip] = load_json(str(p))
    return {"overview": overview, "wms": wms}


# ── 数据分析 ──────────────────────────────────────────────────────────────────

def sum_resource(workers: list[dict], field: str, dim: str) -> float:
    """对 worker 列表中某字段的某维度求和。"""
    return sum(w.get(field, {}).get(dim, 0.0) for w in workers)


def analyze_wm(ip: str, data: dict, floating_cpu: float, floating_mem: float) -> dict[str, Any]:
    """分析单台 WorkManager 的负载指标。"""
    all_workers = data.get("jmWorkers", []) + data.get("tmWorkers", [])

    physical_cpu = sum_resource(all_workers, "physicalResource", "cpuCores")
    physical_mem = sum_resource(all_workers, "physicalResource", "memInMB")
    logical_cpu  = sum_resource(all_workers, "logicalResource",  "cpuCores")
    logical_mem  = sum_resource(all_workers, "logicalResource",  "memInMB")
    profile_cpu  = sum_resource(all_workers, "profiledResource", "cpuCores")
    profile_mem  = sum_resource(all_workers, "profiledResource", "memInMB")

    # 每台机器固定资源（32 core / 64 GB）
    total_cpu = 32.0
    total_mem = 65536.0

    def pct(v: float, total: float) -> float:
        return round(v / total * 100, 2) if total > 0 else 0.0

    def deviation(actual: float, profile: float) -> float:
        if actual == 0:
            return 0.0
        return round((profile - actual) / actual * 100, 2)

    # 逻辑负载来源判断：逻辑负载 == physical * floating_ratio 时来源是实际负载，否则来源是资源负载
    # 精确判断：逐 worker 对比
    actual_based_cpu = sum(
        1 for w in all_workers
        if abs(w.get("logicalResource", {}).get("cpuCores", 0)
               - w.get("physicalResource", {}).get("cpuCores", 0) * floating_cpu) < 1e-6
    )
    resource_based_cpu = len(all_workers) - actual_based_cpu

    actual_based_mem = sum(
        1 for w in all_workers
        if abs(w.get("logicalResource", {}).get("memInMB", 0)
               - w.get("physicalResource", {}).get("memInMB", 0) * floating_mem) < 1e-6
    )
    resource_based_mem = len(all_workers) - actual_based_mem

    return {
        "ip": ip,
        "worker_count": len(all_workers),
        "cpu": {
            "physical_cores": round(physical_cpu, 4),
            "logical_cores":  round(logical_cpu, 4),
            "profile_cores":  round(profile_cpu, 4),
            "physical_pct":   pct(physical_cpu, total_cpu),
            "logical_pct":    pct(logical_cpu, total_cpu),
            "profile_pct":    pct(profile_cpu, total_cpu),
            "dev_profile_vs_physical": deviation(physical_cpu, profile_cpu),
            "dev_profile_vs_logical":  deviation(logical_cpu, profile_cpu),
            "actual_based_workers":    actual_based_cpu,
            "resource_based_workers":  resource_based_cpu,
        },
        "mem": {
            "physical_mb":  round(physical_mem),
            "logical_mb":   round(logical_mem),
            "profile_mb":   round(profile_mem),
            "physical_pct": pct(physical_mem, total_mem),
            "logical_pct":  pct(logical_mem, total_mem),
            "profile_pct":  pct(profile_mem, total_mem),
            "dev_profile_vs_physical": deviation(physical_mem, profile_mem),
            "dev_profile_vs_logical":  deviation(logical_mem, profile_mem),
            "actual_based_workers":    actual_based_mem,
            "resource_based_workers":  resource_based_mem,
        },
    }


def analyze_cluster(overview: dict) -> dict[str, Any]:
    ri = overview.get("resourceInfo", {})
    total_cpu = ri.get("totalResources", {}).get("cpuCores", 0)
    total_mem = ri.get("totalResources", {}).get("memInMB", 0)
    avail_cpu = ri.get("availableResources", {}).get("cpuCores", 0)
    avail_mem = ri.get("availableResources", {}).get("memInMB", 0)
    phys_cpu  = ri.get("physicalResources", {}).get("cpuCores", 0)
    phys_mem  = ri.get("physicalResources", {}).get("memInMB", 0)

    cfg = overview.get("configurationMap", {})

    def pct(v: float, total: float) -> float:
        return round(v / total * 100, 2) if total > 0 else 0.0

    return {
        "total_cpu": total_cpu,
        "total_mem_mb": total_mem,
        "avail_cpu": avail_cpu,
        "avail_mem_mb": avail_mem,
        "used_cpu": round(total_cpu - avail_cpu, 3),
        "used_mem_mb": round(total_mem - avail_mem),
        "phys_cpu": round(phys_cpu, 3),
        "phys_mem_mb": round(phys_mem),
        "used_cpu_pct": pct(total_cpu - avail_cpu, total_cpu),
        "used_mem_pct": pct(total_mem - avail_mem, total_mem),
        "phys_cpu_pct": pct(phys_cpu, total_cpu),
        "phys_mem_pct": pct(phys_mem, total_mem),
        "wm_num": overview.get("workerManagerNum", 0),
        "running_apps": overview.get("runningApplication", 0),
        "floating_cpu": float(cfg.get("physical.resource.floating.ratio.cpu", 1.1)),
        "floating_mem": float(cfg.get("physical.resource.floating.ratio.memory", 1.1)),
    }


# ── HTML 生成 ─────────────────────────────────────────────────────────────────

def risk_class(deviation: float) -> str:
    abs_dev = abs(deviation)
    if abs_dev > DEVIATION_CRIT * 100:
        return "risk-crit"
    if abs_dev > DEVIATION_WARN * 100:
        return "risk-warn"
    return "risk-ok"


def sign(v: float) -> str:
    return f"+{v:.2f}" if v >= 0 else f"{v:.2f}"


def delta_class(v: float) -> str:
    if abs(v) < 0.5:
        return "delta-neutral"
    return "delta-up" if v > 0 else "delta-down"


def gen_html(snaps: dict[str, dict]) -> str:
    snap_ids = list(snaps.keys())
    snap_labels = [SNAP_LABELS.get(s, s) for s in snap_ids]

    # 分析各快照
    analyzed: dict[str, dict] = {}
    for sid, snap in snaps.items():
        cluster = analyze_cluster(snap["overview"])
        wm_stats = {}
        for ip, wm_data in snap["wms"].items():
            wm_stats[ip] = analyze_wm(ip, wm_data, cluster["floating_cpu"], cluster["floating_mem"])
        analyzed[sid] = {"cluster": cluster, "wms": wm_stats}

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── 集群摘要表 ────────────────────────────────────────────────────────────
    cluster_rows = ""
    metrics = [
        ("已用 CPU", "used_cpu_pct", "%"),
        ("已用内存", "used_mem_pct", "%"),
        ("实际 CPU", "phys_cpu_pct", "%"),
        ("实际内存", "phys_mem_pct", "%"),
        ("运行作业", "running_apps", ""),
    ]
    for label, key, unit in metrics:
        row = f"<tr><td>{label}</td>"
        vals = []
        for sid in snap_ids:
            v = analyzed[sid]["cluster"][key]
            vals.append(v)
            row += f"<td>{v}{unit}</td>"
        if len(vals) == 2:
            d = vals[1] - vals[0] if isinstance(vals[1], (int, float)) else 0
            row += f'<td class="{delta_class(d)}">{sign(d)}{unit}</td>'
        row += "</tr>"
        cluster_rows += row

    # ── WM 详情表（每台机器横跨多快照）────────────────────────────────────────
    wm_sections = ""
    for ip in IPS:
        rows = ""
        dims = [
            ("CPU 实际负载", "cpu", "physical_pct", "%"),
            ("CPU 逻辑负载", "cpu", "logical_pct", "%"),
            ("CPU 画像负载", "cpu", "profile_pct", "%"),
            ("CPU 画像 vs 实际偏差", "cpu", "dev_profile_vs_physical", "%"),
            ("CPU 画像 vs 逻辑偏差", "cpu", "dev_profile_vs_logical", "%"),
            ("CPU 实际型 workers",   "cpu", "actual_based_workers", ""),
            ("CPU 资源型 workers",   "cpu", "resource_based_workers", ""),
            ("MEM 实际负载", "mem", "physical_pct", "%"),
            ("MEM 逻辑负载", "mem", "logical_pct", "%"),
            ("MEM 画像负载", "mem", "profile_pct", "%"),
            ("MEM 画像 vs 实际偏差", "mem", "dev_profile_vs_physical", "%"),
            ("MEM 画像 vs 逻辑偏差", "mem", "dev_profile_vs_logical", "%"),
            ("MEM 实际型 workers",   "mem", "actual_based_workers", ""),
            ("MEM 资源型 workers",   "mem", "resource_based_workers", ""),
        ]
        for label, dim, key, unit in dims:
            row = f"<tr><td>{label}</td>"
            vals = []
            for sid in snap_ids:
                wm = analyzed[sid]["wms"].get(ip, {})
                v = wm.get(dim, {}).get(key, "N/A")
                vals.append(v)
                # 偏差列加风险样式
                cls = ""
                if "偏差" in label and isinstance(v, float):
                    cls = f' class="{risk_class(v)}"'
                row += f"<td{cls}>{v}{unit}</td>"
            if len(vals) == 2 and all(isinstance(x, (int, float)) for x in vals):
                d = vals[1] - vals[0]
                row += f'<td class="{delta_class(d)}">{sign(d)}{unit}</td>'
            else:
                row += "<td>—</td>"
            row += "</tr>"
            rows += row

        # 风险标注
        risks = []
        for sid in snap_ids:
            wm = analyzed[sid]["wms"].get(ip, {})
            for dim in ["cpu", "mem"]:
                dev = wm.get(dim, {}).get("dev_profile_vs_physical", 0)
                if abs(dev) > DEVIATION_CRIT * 100:
                    risks.append(f"[{SNAP_LABELS.get(sid,sid)}] {dim.upper()} 画像偏差严重: {dev:+.1f}%")
                elif abs(dev) > DEVIATION_WARN * 100:
                    risks.append(f"[{SNAP_LABELS.get(sid,sid)}] {dim.upper()} 画像偏差较大: {dev:+.1f}%")
        risk_html = ""
        if risks:
            items = "".join(f"<li>{r}</li>" for r in risks)
            risk_html = f'<div class="risk-box"><strong>风险提示</strong><ul>{items}</ul></div>'

        header_cells = "".join(f"<th>{l}</th>" for l in snap_labels)
        wm_sections += f"""
        <div class="wm-section">
          <h3>WorkManager: {ip}</h3>
          {risk_html}
          <table>
            <thead><tr><th>指标</th>{header_cells}<th>变化量</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
        """

    # ── Worker 级别明细（每个快照的 worker 列表）────────────────────────────────
    worker_detail_sections = ""
    for ip in IPS:
        tabs_html = ""
        panels_html = ""
        for i, sid in enumerate(snap_ids):
            label = SNAP_LABELS.get(sid, sid)
            snap_data = snaps[sid]["wms"].get(ip, {})
            all_workers = snap_data.get("jmWorkers", []) + snap_data.get("tmWorkers", [])
            cluster_info = analyzed[sid]["cluster"]

            worker_rows = ""
            for w in all_workers:
                wid = w.get("workerId", {}).get("workerId", "unknown")
                is_jm = w.get("jobManager", False)
                role = "JM" if is_jm else "TM"
                phys_cpu = w.get("physicalResource", {}).get("cpuCores", 0)
                phys_mem = w.get("physicalResource", {}).get("memInMB", 0)
                logi_cpu = w.get("logicalResource", {}).get("cpuCores", 0)
                logi_mem = w.get("logicalResource", {}).get("memInMB", 0)
                prof_cpu = w.get("profiledResource", {}).get("cpuCores", 0)
                prof_mem = w.get("profiledResource", {}).get("memInMB", 0)

                dev_cpu = (prof_cpu - phys_cpu) / phys_cpu * 100 if phys_cpu else 0
                dev_mem = (prof_mem - phys_mem) / phys_mem * 100 if phys_mem else 0

                # 逻辑负载来源
                fr_cpu = cluster_info["floating_cpu"]
                fr_mem = cluster_info["floating_mem"]
                src_cpu = "实际型" if abs(logi_cpu - phys_cpu * fr_cpu) < 1e-6 else "资源型"
                src_mem = "实际型" if abs(logi_mem - phys_mem * fr_mem) < 1e-6 else "资源型"

                dev_cpu_cls = risk_class(dev_cpu)
                dev_mem_cls = risk_class(dev_mem)

                worker_rows += f"""
                <tr>
                  <td><code>{wid}</code></td>
                  <td><span class="badge badge-{'jm' if is_jm else 'tm'}">{role}</span></td>
                  <td>{phys_cpu:.4f}</td>
                  <td>{logi_cpu:.4f} <small>({src_cpu})</small></td>
                  <td>{prof_cpu:.4f}</td>
                  <td class="{dev_cpu_cls}">{dev_cpu:+.1f}%</td>
                  <td>{phys_mem}</td>
                  <td>{logi_mem} <small>({src_mem})</small></td>
                  <td>{prof_mem}</td>
                  <td class="{dev_mem_cls}">{dev_mem:+.1f}%</td>
                </tr>
                """

            active = "active" if i == 0 else ""
            tab_id = f"tab_{ip.replace('.','_')}_{sid}"
            tabs_html += f'<button class="tab-btn {active}" onclick="switchTab(\'{tab_id}\')">{label}</button>'
            panels_html += f"""
            <div id="{tab_id}" class="tab-panel {active}">
              <table class="worker-table">
                <thead>
                  <tr>
                    <th>Worker ID</th><th>角色</th>
                    <th>实际CPU(core)</th><th>逻辑CPU(core)</th><th>画像CPU(core)</th><th>CPU偏差</th>
                    <th>实际MEM(MB)</th><th>逻辑MEM(MB)</th><th>画像MEM(MB)</th><th>MEM偏差</th>
                  </tr>
                </thead>
                <tbody>{worker_rows}</tbody>
              </table>
            </div>
            """

        worker_detail_sections += f"""
        <div class="wm-section">
          <h3>Worker 明细: {ip}</h3>
          <div class="tab-bar">{tabs_html}</div>
          {panels_html}
        </div>
        """

    # ── 集群级别表头 ──────────────────────────────────────────────────────────
    cluster_header = "".join(f"<th>{l}</th>" for l in snap_labels)
    if len(snap_ids) == 2:
        cluster_header += "<th>变化量</th>"

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Flink 集群画像负载 — 时序对比分析报告</title>
<style>
  :root {{
    --bg: #0d1117; --surface: #161b22; --surface2: #21262d;
    --border: #30363d; --text: #c9d1d9; --text-dim: #8b949e;
    --accent: #58a6ff; --green: #3fb950; --yellow: #d29922; --red: #f85149;
    --purple: #bc8cff;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'SF Mono', 'Fira Code', monospace; font-size: 13px; line-height: 1.6; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}
  h1 {{ font-size: 20px; color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 12px; margin-bottom: 20px; }}
  h2 {{ font-size: 15px; color: var(--accent); margin: 28px 0 12px; padding-left: 8px; border-left: 3px solid var(--accent); }}
  h3 {{ font-size: 13px; color: var(--text-dim); margin-bottom: 10px; }}
  .meta {{ color: var(--text-dim); font-size: 11px; margin-bottom: 24px; }}
  .meta span {{ margin-right: 20px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; background: var(--surface); border-radius: 6px; overflow: hidden; }}
  th {{ background: var(--surface2); color: var(--text-dim); font-weight: 500; padding: 8px 12px; text-align: right; font-size: 11px; letter-spacing: 0.5px; }}
  th:first-child {{ text-align: left; }}
  td {{ padding: 7px 12px; text-align: right; border-top: 1px solid var(--border); font-variant-numeric: tabular-nums; }}
  td:first-child {{ text-align: left; color: var(--text-dim); }}
  tr:hover td {{ background: var(--surface2); }}
  .risk-ok   {{ color: var(--green); }}
  .risk-warn {{ color: var(--yellow); font-weight: 600; }}
  .risk-crit {{ color: var(--red); font-weight: 700; }}
  .delta-up      {{ color: var(--red); }}
  .delta-down    {{ color: var(--green); }}
  .delta-neutral {{ color: var(--text-dim); }}
  .risk-box {{ background: rgba(248,81,73,0.1); border: 1px solid var(--red); border-radius: 6px; padding: 10px 14px; margin-bottom: 12px; font-size: 12px; color: var(--red); }}
  .risk-box ul {{ padding-left: 18px; margin-top: 4px; }}
  .wm-section {{ margin-bottom: 28px; padding: 16px; background: var(--surface); border-radius: 8px; border: 1px solid var(--border); }}
  .badge {{ padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; }}
  .badge-jm {{ background: rgba(88,166,255,0.2); color: var(--accent); }}
  .badge-tm {{ background: rgba(63,185,80,0.2); color: var(--green); }}
  .tab-bar {{ display: flex; gap: 4px; margin-bottom: 12px; }}
  .tab-btn {{ background: var(--surface2); border: 1px solid var(--border); color: var(--text-dim); padding: 5px 14px; border-radius: 4px; cursor: pointer; font-size: 12px; font-family: inherit; }}
  .tab-btn.active {{ background: var(--accent); color: #000; border-color: var(--accent); }}
  .tab-panel {{ display: none; overflow-x: auto; }}
  .tab-panel.active {{ display: block; }}
  .worker-table td {{ font-size: 11px; padding: 5px 8px; }}
  .worker-table td:first-child {{ max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 10px; }}
  code {{ font-family: inherit; font-size: 10px; color: var(--purple); }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 24px; }}
  .summary-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 14px 18px; }}
  .summary-card .label {{ color: var(--text-dim); font-size: 11px; margin-bottom: 4px; }}
  .summary-card .value {{ font-size: 20px; font-weight: 700; color: var(--accent); }}
  .summary-card .sub {{ font-size: 11px; color: var(--text-dim); margin-top: 2px; }}
</style>
</head>
<body>
<div class="container">
  <h1>Flink 集群画像负载 — 时序对比分析报告</h1>
  <div class="meta">
    <span>集群: eg168-cluster-pre</span>
    <span>采样点: {" / ".join(snap_labels)}</span>
    <span>间隔: ~5 min</span>
    <span>生成时间: {now}</span>
    <span>Floating Ratio — CPU: {FLOATING_RATIO_CPU} / MEM: {FLOATING_RATIO_MEM}</span>
  </div>

  <h2>集群维度汇总</h2>
  <table>
    <thead><tr><th>指标</th>{cluster_header}</tr></thead>
    <tbody>{cluster_rows}</tbody>
  </table>

  <h2>WorkManager 负载对比</h2>
  {wm_sections}

  <h2>Worker 粒度明细</h2>
  {worker_detail_sections}
</div>
<script>
function switchTab(id) {{
  const panel = document.getElementById(id);
  if (!panel) return;
  const container = panel.closest('.wm-section');
  container.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  container.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  panel.classList.add('active');
  container.querySelectorAll('.tab-btn').forEach(b => {{
    if (b.getAttribute('onclick').includes(id)) b.classList.add('active');
  }});
}}
</script>
</body>
</html>"""
    return html


# ── 入口 ──────────────────────────────────────────────────────────────────────

def main() -> None:
    snaps: dict[str, dict] = {}
    for sid in SNAP_LABELS:
        try:
            snaps[sid] = load_snap(sid)
            print(f"  loaded {sid}: {len(snaps[sid]['wms'])} WMs")
        except FileNotFoundError as e:
            print(f"  skip {sid}: {e}")

    if not snaps:
        raise SystemExit("没有可用的快照数据，退出。")

    html = gen_html(snaps)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"\n报告已生成: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
