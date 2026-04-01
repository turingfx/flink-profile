import json
from datetime import datetime

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
WM_CPU_TOTAL = 24.0
WM_MEM_TOTAL_MB = 49152
CLUSTER_CPU_TOTAL = 96.0
CLUSTER_MEM_TOTAL_MB = 196608
FLOATING_RATIO_CPU = 1.1
FLOATING_RATIO_MEM = 1.1

machines = {}
cluster_totals = dict(actual_cpu=0, logical_cpu=0, profile_cpu=0,
                      actual_mem=0, logical_mem=0, profile_mem=0)

for ip in ["33.190.84.129", "33.190.85.106", "33.190.85.70", "33.190.85.103"]:
    with open(f'/tmp/wm_{ip}.json') as f:
        d = json.load(f)
    workers = d.get('jmWorkers', []) + d.get('tmWorkers', [])

    wlist = []
    for w in workers:
        wid = w['workerId']['workerId']
        pc = w['physicalResource']['cpuCores']
        lc = w['logicalResource']['cpuCores']
        fc = w['profiledResource']['cpuCores']
        rc = w['requestedResource']['cpuCores']
        pm = w['physicalResource']['memInMB']
        lm = w['logicalResource']['memInMB']
        fm = w['profiledResource']['memInMB']
        rm = w['requestedResource']['memInMB']
        wlist.append(dict(id=wid, is_jm=w.get('jobManager', False),
                          actual_cpu=pc, logical_cpu=lc, profile_cpu=fc, req_cpu=rc,
                          actual_mem=pm, logical_mem=lm, profile_mem=fm, req_mem=rm))

    ta_cpu = sum(w['actual_cpu'] for w in wlist)
    tl_cpu = sum(w['logical_cpu'] for w in wlist)
    tp_cpu = sum(w['profile_cpu'] for w in wlist)
    ta_mem = sum(w['actual_mem'] for w in wlist)
    tl_mem = sum(w['logical_mem'] for w in wlist)
    tp_mem = sum(w['profile_mem'] for w in wlist)

    machines[ip] = dict(
        workers=wlist,
        actual_cpu=ta_cpu, logical_cpu=tl_cpu, profile_cpu=tp_cpu,
        actual_mem=ta_mem, logical_mem=tl_mem, profile_mem=tp_mem,
        actual_cpu_pct=ta_cpu / WM_CPU_TOTAL * 100,
        logical_cpu_pct=tl_cpu / WM_CPU_TOTAL * 100,
        profile_cpu_pct=tp_cpu / WM_CPU_TOTAL * 100,
        actual_mem_pct=ta_mem / WM_MEM_TOTAL_MB * 100,
        logical_mem_pct=tl_mem / WM_MEM_TOTAL_MB * 100,
        profile_mem_pct=tp_mem / WM_MEM_TOTAL_MB * 100,
    )
    cluster_totals['actual_cpu'] += ta_cpu
    cluster_totals['logical_cpu'] += tl_cpu
    cluster_totals['profile_cpu'] += tp_cpu
    cluster_totals['actual_mem'] += ta_mem
    cluster_totals['logical_mem'] += tl_mem
    cluster_totals['profile_mem'] += tp_mem


def dev(profile, actual):
    if actual == 0:
        return 0
    return (profile - actual) / actual * 100


def gauge_color(pct):
    if pct >= 95:
        return '#ef4444'
    if pct >= 80:
        return '#f97316'
    if pct >= 60:
        return '#eab308'
    return '#22c55e'


def worker_rows(ip):
    rows = []
    for w in machines[ip]['workers']:
        cpu_dev = dev(w['profile_cpu'], w['actual_cpu'])
        mem_dev = dev(w['profile_mem'], w['actual_mem'])
        cpu_cls = 'high' if abs(cpu_dev) > 50 else ('med' if abs(cpu_dev) > 20 else 'ok')
        mem_cls = 'high' if abs(mem_dev) > 50 else ('med' if abs(mem_dev) > 20 else 'ok')
        wtype = 'JM' if w['is_jm'] else 'TM'
        tag_cls = 'tag-jm' if w['is_jm'] else 'tag-tm'
        cpu_dev_str = ('+' if cpu_dev >= 0 else '') + f'{cpu_dev:.1f}%'
        mem_dev_str = ('+' if mem_dev >= 0 else '') + f'{mem_dev:.1f}%'
        rows.append(
            f'<tr>'
            f'<td><span class="tag {tag_cls}">{wtype}</span>{w["id"]}</td>'
            f'<td>{w["actual_cpu"]:.3f} ({w["actual_cpu"]/WM_CPU_TOTAL*100:.1f}%)</td>'
            f'<td>{w["logical_cpu"]:.3f} ({w["logical_cpu"]/WM_CPU_TOTAL*100:.1f}%)</td>'
            f'<td>{w["profile_cpu"]:.3f} ({w["profile_cpu"]/WM_CPU_TOTAL*100:.1f}%)</td>'
            f'<td class="{cpu_cls}">{cpu_dev_str}</td>'
            f'<td>{w["actual_mem"]/1024:.2f} ({w["actual_mem"]/WM_MEM_TOTAL_MB*100:.1f}%)</td>'
            f'<td>{w["logical_mem"]/1024:.2f} ({w["logical_mem"]/WM_MEM_TOTAL_MB*100:.1f}%)</td>'
            f'<td>{w["profile_mem"]/1024:.2f} ({w["profile_mem"]/WM_MEM_TOTAL_MB*100:.1f}%)</td>'
            f'<td class="{mem_cls}">{mem_dev_str}</td>'
            f'</tr>'
        )
    return '\n'.join(rows)


def machine_cards():
    cards = []
    for ip, m in machines.items():
        cpu_dev = dev(m['profile_cpu_pct'], m['actual_cpu_pct'])
        mem_dev = dev(m['profile_mem_pct'], m['actual_mem_pct'])
        if m['profile_mem_pct'] >= 100:
            risk = '<span class="risk-badge">内存画像超限</span>'
        elif m['profile_mem_pct'] >= 90:
            risk = '<span class="risk-badge warn">内存画像偏高</span>'
        else:
            risk = ''

        cpu_dev_str = ('+' if cpu_dev >= 0 else '') + f'{cpu_dev:.1f}% vs 实际'
        mem_dev_str = ('+' if mem_dev >= 0 else '') + f'{mem_dev:.1f}% vs 实际'
        cpu_dev_cls = 'dev-up' if cpu_dev >= 0 else 'dev-down'
        mem_dev_cls = 'dev-up' if mem_dev >= 0 else 'dev-down'

        def metric_block(label, cores_or_gb, pct, dev_str=None, dev_cls=None, unit='核'):
            bar_w = min(pct, 100)
            color = gauge_color(pct)
            dev_html = (f'<span class="dev-badge {dev_cls}">{dev_str}</span>' if dev_str else '')
            return (
                f'<div class="metric-block">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value">{cores_or_gb:.2f} {unit}</div>'
                f'<div class="progress-bar"><div class="progress-fill" style="width:{bar_w:.1f}%;background:{color}"></div></div>'
                f'<div class="metric-pct">{pct:.1f}%{dev_html}</div>'
                f'</div>'
            )

        blocks = (
            metric_block('CPU 实际', m['actual_cpu'], m['actual_cpu_pct']) +
            metric_block('CPU 逻辑', m['logical_cpu'], m['logical_cpu_pct']) +
            metric_block('CPU 画像', m['profile_cpu'], m['profile_cpu_pct'], cpu_dev_str, cpu_dev_cls) +
            metric_block('内存 实际', m['actual_mem'] / 1024, m['actual_mem_pct'], unit='GB') +
            metric_block('内存 逻辑', m['logical_mem'] / 1024, m['logical_mem_pct'], unit='GB') +
            metric_block('内存 画像', m['profile_mem'] / 1024, m['profile_mem_pct'], mem_dev_str, mem_dev_cls, unit='GB')
        )

        cards.append(
            f'<div class="machine-card">'
            f'<div class="machine-header">'
            f'<div><div class="machine-ip">{ip}</div>'
            f'<div class="machine-sub">{len(m["workers"])} workers &nbsp;|&nbsp; 24 CPU核 / 48 GB内存</div></div>'
            f'<div>{risk}</div></div>'
            f'<div class="metrics-grid">{blocks}</div>'
            f'<details class="worker-detail">'
            f'<summary>展开 Worker 明细（{len(m["workers"])} 个）</summary>'
            f'<table class="worker-table"><thead><tr>'
            f'<th>Worker ID</th>'
            f'<th>CPU 实际</th><th>CPU 逻辑</th><th>CPU 画像</th><th>CPU 偏差</th>'
            f'<th>内存 实际(GB)</th><th>内存 逻辑(GB)</th><th>内存 画像(GB)</th><th>内存 偏差</th>'
            f'</tr></thead><tbody>{worker_rows(ip)}</tbody></table>'
            f'</details></div>'
        )
    return '\n'.join(cards)


def machine_table_rows():
    rows = []
    for ip, m in machines.items():
        cpu_dev = dev(m['profile_cpu_pct'], m['actual_cpu_pct'])
        mem_dev = dev(m['profile_mem_pct'], m['actual_mem_pct'])
        rows.append(
            f'<div class="cluster-row data-row">'
            f'<div class="row-label" style="font-family:monospace;font-size:12px">{ip}</div>'
            f'<div class="cell row-actual">{m["actual_cpu"]:.1f}核 ({m["actual_cpu_pct"]:.1f}%)</div>'
            f'<div class="cell row-logical">{m["logical_cpu"]:.1f}核 ({m["logical_cpu_pct"]:.1f}%)</div>'
            f'<div class="cell row-profile">{m["profile_cpu"]:.1f}核 ({m["profile_cpu_pct"]:.1f}%)</div>'
            f'<div class="cell row-actual">{m["actual_mem"]/1024:.1f}GB ({m["actual_mem_pct"]:.1f}%)</div>'
            f'<div class="cell row-logical">{m["logical_mem"]/1024:.1f}GB ({m["logical_mem_pct"]:.1f}%)</div>'
            f'<div class="cell row-profile">{m["profile_mem"]/1024:.1f}GB ({m["profile_mem_pct"]:.1f}%)</div>'
            f'</div>'
        )
    return '\n'.join(rows)


# 集群统计
cl_cpu_actual_pct = cluster_totals['actual_cpu'] / CLUSTER_CPU_TOTAL * 100
cl_cpu_logical_pct = cluster_totals['logical_cpu'] / CLUSTER_CPU_TOTAL * 100
cl_cpu_profile_pct = cluster_totals['profile_cpu'] / CLUSTER_CPU_TOTAL * 100
cl_mem_actual_pct = cluster_totals['actual_mem'] / CLUSTER_MEM_TOTAL_MB * 100
cl_mem_logical_pct = cluster_totals['logical_mem'] / CLUSTER_MEM_TOTAL_MB * 100
cl_mem_profile_pct = cluster_totals['profile_mem'] / CLUSTER_MEM_TOTAL_MB * 100
cl_cpu_dev = dev(cl_cpu_profile_pct, cl_cpu_actual_pct)
cl_mem_dev = dev(cl_mem_profile_pct, cl_mem_actual_pct)
mem_85_70_dev = dev(machines['33.190.85.70']['profile_mem_pct'], machines['33.190.85.70']['actual_mem_pct'])
mem_106_pct = machines['33.190.85.106']['profile_mem_pct']
mem_103_pct = machines['33.190.85.103']['profile_mem_pct']
cpu_85_70_pct = machines['33.190.85.70']['actual_cpu_pct']
mem_85_70_pct = machines['33.190.85.70']['actual_mem_pct']

css = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f0f2f5; color: #1a1a2e; }
  .header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); color: white; padding: 32px 40px; position: relative; }
  .header h1 { font-size: 24px; font-weight: 700; margin-bottom: 6px; }
  .header .meta { font-size: 13px; opacity: 0.7; }
  .header .cluster-name { font-size: 14px; opacity: 0.9; margin-top: 4px; }
  .flink-link { position: absolute; top: 32px; right: 40px; display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); border-radius: 8px; color: white; text-decoration: none; font-size: 13px; font-weight: 500; transition: all 0.2s; }
  .flink-link:hover { background: rgba(255,255,255,0.25); border-color: rgba(255,255,255,0.5); }
  .container { max-width: 1400px; margin: 0 auto; padding: 28px 24px; }
  .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }
  .summary-card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
  .s-label { font-size: 12px; color: #6b7280; margin-bottom: 8px; }
  .s-val { font-size: 28px; font-weight: 700; color: #1a1a2e; }
  .s-sub { font-size: 13px; color: #6b7280; margin-top: 4px; }
  .s-badge { display: inline-block; margin-top: 8px; padding: 2px 8px; border-radius: 99px; font-size: 12px; font-weight: 600; }
  .badge-warn { background: #fef3c7; color: #92400e; }
  .badge-ok { background: #d1fae5; color: #065f46; }
  .badge-danger { background: #fee2e2; color: #991b1b; }
  .section-title { font-size: 16px; font-weight: 700; color: #1a1a2e; margin-bottom: 14px; padding-left: 10px; border-left: 4px solid #0f3460; }
  .cluster-overview { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 28px; }
  .cluster-row { display: grid; grid-template-columns: 140px repeat(6, 1fr); gap: 0; }
  .header-row { font-size: 12px; color: #6b7280; font-weight: 600; padding-bottom: 10px; border-bottom: 1px solid #f3f4f6; margin-bottom: 12px; }
  .data-row { padding: 10px 0; border-bottom: 1px solid #f9fafb; align-items: center; }
  .cell { padding: 0 8px; font-size: 13px; }
  .row-label { font-weight: 600; font-size: 13px; padding: 0 8px; }
  .row-actual { color: #374151; }
  .row-logical { color: #2563eb; }
  .row-profile { color: #7c3aed; }
  .machine-card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 20px; }
  .machine-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 18px; }
  .machine-ip { font-size: 18px; font-weight: 700; color: #1a1a2e; font-family: monospace; }
  .machine-sub { font-size: 12px; color: #9ca3af; margin-top: 4px; }
  .risk-badge { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; background: #fee2e2; color: #991b1b; }
  .risk-badge.warn { background: #fef3c7; color: #92400e; }
  .metrics-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 14px; margin-bottom: 16px; }
  .metric-block { background: #f9fafb; border-radius: 8px; padding: 12px; }
  .metric-label { font-size: 11px; color: #6b7280; margin-bottom: 6px; font-weight: 600; text-transform: uppercase; }
  .metric-value { font-size: 16px; font-weight: 700; color: #1a1a2e; margin-bottom: 8px; }
  .progress-bar { height: 6px; background: #e5e7eb; border-radius: 99px; overflow: hidden; margin-bottom: 4px; }
  .progress-fill { height: 100%; border-radius: 99px; }
  .metric-pct { font-size: 12px; color: #374151; }
  .dev-badge { display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-left: 4px; }
  .dev-up { background: #fef9c3; color: #854d0e; }
  .dev-down { background: #dcfce7; color: #166534; }
  .worker-detail { margin-top: 12px; }
  .worker-detail summary { cursor: pointer; font-size: 13px; color: #4b5563; padding: 8px 0; user-select: none; }
  .worker-detail summary:hover { color: #1a1a2e; }
  .worker-table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 12px; }
  .worker-table th { background: #f3f4f6; padding: 8px 10px; text-align: left; font-weight: 600; color: #374151; border-bottom: 2px solid #e5e7eb; }
  .worker-table td { padding: 7px 10px; border-bottom: 1px solid #f3f4f6; color: #374151; }
  .worker-table tr:hover td { background: #fafafa; }
  .tag { display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; margin-right: 6px; }
  .tag-jm { background: #dbeafe; color: #1d4ed8; }
  .tag-tm { background: #f3e8ff; color: #7e22ce; }
  .ok { color: #16a34a; font-weight: 600; }
  .med { color: #d97706; font-weight: 600; }
  .high { color: #dc2626; font-weight: 600; }
  .findings { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 28px; }
  .finding-item { display: flex; gap: 14px; padding: 14px 0; border-bottom: 1px solid #f3f4f6; }
  .finding-item:last-child { border-bottom: none; }
  .finding-icon { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; }
  .icon-warn { background: #fef3c7; }
  .icon-info { background: #dbeafe; }
  .finding-title { font-size: 14px; font-weight: 700; color: #1a1a2e; margin-bottom: 4px; }
  .finding-desc { font-size: 13px; color: #6b7280; line-height: 1.6; }
  .footer { text-align: center; font-size: 12px; color: #9ca3af; padding: 24px; }
"""

cpu_badge = 'badge-warn' if cl_cpu_actual_pct >= 60 else 'badge-ok'
cpu_label = '偏高' if cl_cpu_actual_pct >= 60 else '正常'
mem_badge = 'badge-warn' if cl_mem_actual_pct >= 60 else 'badge-ok'
mem_label = '偏高' if cl_mem_actual_pct >= 60 else '正常'

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Flink 集群画像负载效果评估报告</title>
<style>{css}</style>
</head>
<body>
<div class="header">
  <a href="https://mybkcosmos.mybank.cn/proxy/cosmos/flink/cluster/eg168-cluster-pre/eg168-cluster-pre-service.blink-operator.svc.eg168.mybank.cn:8081/#/overview" target="_blank" class="flink-link">🔗 Flink UI</a>
  <h1>Flink 集群画像负载效果评估报告</h1>
  <div class="cluster-name">集群：eg168-cluster-pre</div>
  <div class="meta">数据采集时间：{timestamp} &nbsp;|&nbsp; Floating Ratio: CPU×{FLOATING_RATIO_CPU} / MEM×{FLOATING_RATIO_MEM} &nbsp;|&nbsp; 共 4 台 WorkManager</div>
</div>

<div class="container">

<div class="summary-grid">
  <div class="summary-card">
    <div class="s-label">集群 CPU 实际占用</div>
    <div class="s-val">{cl_cpu_actual_pct:.1f}%</div>
    <div class="s-sub">{cluster_totals['actual_cpu']:.1f} / {CLUSTER_CPU_TOTAL:.0f} 核</div>
    <span class="s-badge {cpu_badge}">{cpu_label}</span>
  </div>
  <div class="summary-card">
    <div class="s-label">集群内存实际占用</div>
    <div class="s-val">{cl_mem_actual_pct:.1f}%</div>
    <div class="s-sub">{cluster_totals['actual_mem']/1024:.1f} / {CLUSTER_MEM_TOTAL_MB/1024:.0f} GB</div>
    <span class="s-badge {mem_badge}">{mem_label}</span>
  </div>
  <div class="summary-card">
    <div class="s-label">画像 CPU 偏差（vs 实际）</div>
    <div class="s-val">+{cl_cpu_dev:.1f}%</div>
    <div class="s-sub">画像 {cl_cpu_profile_pct:.1f}% vs 实际 {cl_cpu_actual_pct:.1f}%</div>
    <span class="s-badge badge-warn">画像偏高</span>
  </div>
  <div class="summary-card">
    <div class="s-label">画像内存偏差（vs 实际）</div>
    <div class="s-val">+{cl_mem_dev:.1f}%</div>
    <div class="s-sub">画像 {cl_mem_profile_pct:.1f}% vs 实际 {cl_mem_actual_pct:.1f}%</div>
    <span class="s-badge badge-danger">偏差较大</span>
  </div>
</div>

<div class="section-title">集群维度负载汇总</div>
<div class="cluster-overview">
  <div class="cluster-row header-row">
    <div class="cell">维度</div>
    <div class="cell">CPU 实际</div><div class="cell">CPU 逻辑</div><div class="cell">CPU 画像</div>
    <div class="cell">内存 实际</div><div class="cell">内存 逻辑</div><div class="cell">内存 画像</div>
  </div>
  <div class="cluster-row data-row">
    <div class="row-label">集群合计</div>
    <div class="cell row-actual">{cluster_totals['actual_cpu']:.1f}核 ({cl_cpu_actual_pct:.1f}%)</div>
    <div class="cell row-logical">{cluster_totals['logical_cpu']:.1f}核 ({cl_cpu_logical_pct:.1f}%)</div>
    <div class="cell row-profile">{cluster_totals['profile_cpu']:.1f}核 ({cl_cpu_profile_pct:.1f}%)</div>
    <div class="cell row-actual">{cluster_totals['actual_mem']/1024:.1f}GB ({cl_mem_actual_pct:.1f}%)</div>
    <div class="cell row-logical">{cluster_totals['logical_mem']/1024:.1f}GB ({cl_mem_logical_pct:.1f}%)</div>
    <div class="cell row-profile">{cluster_totals['profile_mem']/1024:.1f}GB ({cl_mem_profile_pct:.1f}%)</div>
  </div>
  {machine_table_rows()}
</div>

<div class="section-title">关键发现</div>
<div class="findings">
  <div class="finding-item">
    <div class="finding-icon icon-info">💡</div>
    <div>
      <div class="finding-title">画像值 = 逻辑负载（当前行为）</div>
      <div class="finding-desc">实时数据显示所有机器的画像负载与逻辑负载完全一致，说明当前画像直接采用逻辑资源（申请量按 floating ratio 换算），并非基于实际运行时行为的预测模型输出。画像功能（<code>workermanager.profile.switch=false</code>）目前处于关闭状态。</div>
    </div>
  </div>
  <div class="finding-item">
    <div class="finding-icon icon-warn">⚠️</div>
    <div>
      <div class="finding-title">画像整体高于实际：CPU +{cl_cpu_dev:.1f}%，内存 +{cl_mem_dev:.1f}%</div>
      <div class="finding-desc">集群维度画像 CPU 比实际高 {cl_cpu_dev:.1f}%，内存高 {cl_mem_dev:.1f}%。这意味着画像预留了比实际需要更多的资源，调度器倾向于认为机器负载更高，会抑制新作业调度到这些机器，造成资源浪费。</div>
    </div>
  </div>
  <div class="finding-item">
    <div class="finding-icon icon-warn">⚠️</div>
    <div>
      <div class="finding-title">负载不均衡：33.190.85.70 明显轻载</div>
      <div class="finding-desc">33.190.85.70 的 CPU 实际负载仅 {cpu_85_70_pct:.1f}%、内存 {mem_85_70_pct:.1f}%，远低于集群平均水平（CPU {cl_cpu_actual_pct:.1f}%），但其内存画像偏差达 +{mem_85_70_dev:.1f}%。负载不均会加剧其他机器的压力，建议优化调度策略向该机器倾斜。</div>
    </div>
  </div>
  <div class="finding-item">
    <div class="finding-icon icon-warn">🚨</div>
    <div>
      <div class="finding-title">33.190.85.106 / 33.190.85.103 内存画像接近或超过 100%</div>
      <div class="finding-desc">33.190.85.106 内存画像 {mem_106_pct:.1f}%，33.190.85.103 内存画像 {mem_103_pct:.1f}%，均接近或超过逻辑上限，新作业将无法调度至这两台机器，在 33.190.85.70 轻载的情况下，整体调度效率受到明显影响。</div>
    </div>
  </div>
  <div class="finding-item">
    <div class="finding-icon icon-info">📊</div>
    <div>
      <div class="finding-title">内存偏差系统性大于 CPU 偏差（{cl_mem_dev/cl_cpu_dev:.1f}x）</div>
      <div class="finding-desc">CPU 画像偏差 +{cl_cpu_dev:.1f}%，内存画像偏差 +{cl_mem_dev:.1f}%，内存偏差约为 CPU 的 {cl_mem_dev/cl_cpu_dev:.1f} 倍。说明作业内存实际使用率（实际占申请量之比）整体偏低，内存资源存在明显浪费，申请量远大于实际需要。</div>
    </div>
  </div>
</div>

<div class="section-title">各 WorkManager 详情</div>
{machine_cards()}

<div class="footer">
  eg168-cluster-pre &nbsp;|&nbsp; 数据采集：{timestamp} &nbsp;|&nbsp; Flink 集群画像负载评估
</div>
</div>
</body>
</html>"""

output_path = 'output/cluster_load_report.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"报告已生成: {output_path}")
