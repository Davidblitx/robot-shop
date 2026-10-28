import json, pathlib, textwrap

DS = {"type": "prometheus", "uid": "${datasource}"}
PROBE = 'job=~"probe/.*robot-shop-web"'

def panel(pid, title, x, y, w, h, targets, kind="timeseries", unit="short", desc="", thresholds=None):
    defaults = {"unit": unit}
    if unit == "percentunit":
        defaults["min"] = 0
        defaults["max"] = 1
    if thresholds:
        defaults["thresholds"] = {"mode": "absolute", "steps": thresholds}
    return {
        "id": pid, "type": kind, "title": title, "description": desc,
        "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "fieldConfig": {"defaults": defaults, "overrides": []},
        "targets": [
            {"datasource": DS, "expr": e, "legendFormat": l, "refId": chr(65 + i)}
            for i, (e, l) in enumerate(targets)
        ],
    }

good_high = [{"color": "red", "value": None}, {"color": "orange", "value": 0.95}, {"color": "green", "value": 0.99}]
bad_high = [{"color": "green", "value": None}, {"color": "orange", "value": 0.01}, {"color": "red", "value": 0.05}]

panels = [
    panel(1, "Availability (5m)", 0, 0, 6, 4,
          [(f"avg(avg_over_time(probe_success{{{PROBE}}}[5m]))", "availability")],
          kind="stat", unit="percentunit", thresholds=good_high,
          desc="Share of successful HTTP probes against the web service."),
    panel(2, "Error ratio (5m)", 6, 0, 6, 4,
          [(f"1 - avg(avg_over_time(probe_success{{{PROBE}}}[5m]))", "errors")],
          kind="stat", unit="percentunit", thresholds=bad_high,
          desc="Share of failed HTTP probes."),
    panel(3, "Payment pods ready", 12, 0, 6, 4,
          [('sum(kube_pod_status_ready{namespace="robot-shop",condition="true",pod=~"payment-.*"})', "ready")],
          kind="stat"),
    panel(4, "Web pods ready", 18, 0, 6, 4,
          [('sum(kube_pod_status_ready{namespace="robot-shop",condition="true",pod=~"web-.*"})', "ready")],
          kind="stat"),
    panel(5, "Requests: user actions per second", 0, 4, 12, 8,
          [('sum(rate(items_added{service="cart"}[5m]))', "cart items added/s"),
           ('sum(rate(sold_count_total{service="payment"}[5m]))', "payment items sold/s")],
          unit="ops", desc="Throughput from the cart and payment business counters."),
    panel(6, "Errors: failed probes by endpoint", 12, 4, 12, 8,
          [(f"1 - avg_over_time(probe_success{{{PROBE}}}[1m])", "{{instance}}")],
          unit="percentunit", desc="0 means healthy, 1 means every probe failed."),
    panel(7, "Latency: probe duration", 0, 12, 12, 8,
          [(f"probe_duration_seconds{{{PROBE}}}", "{{instance}}")],
          unit="s", desc="Time to answer for each probed endpoint."),
    panel(8, "HTTP status code by endpoint", 12, 12, 6, 8,
          [(f"probe_http_status_code{{{PROBE}}}", "{{instance}}")]),
    panel(9, "Pod restarts (15m)", 18, 12, 6, 8,
          [('sum by (pod) (increase(kube_pod_container_status_restarts_total{namespace="robot-shop"}[15m]))', "{{pod}}")]),
]

dash = {
    "uid": "robot-shop-red",
    "title": "Robot Shop: Requests, Errors, Latency",
    "tags": ["robot-shop", "slo"],
    "timezone": "browser",
    "schemaVersion": 39,
    "version": 1,
    "refresh": "15s",
    "time": {"from": "now-1h", "to": "now"},
    "templating": {"list": [{"name": "datasource", "label": "Data source",
                             "type": "datasource", "query": "prometheus",
                             "current": {}, "hide": 0}]},
    "panels": panels,
}

d = pathlib.Path("observability/dashboards")
body = json.dumps(dash, indent=2)
(d / "robot-shop-red-metrics.json").write_text(body + "\n")
cm = (
    "apiVersion: v1\nkind: ConfigMap\nmetadata:\n"
    "  name: robot-shop-red-dashboard\n  namespace: monitoring\n"
    "  labels:\n    grafana_dashboard: \"1\"\n"
    "data:\n  robot-shop-red-metrics.json: |\n"
    + textwrap.indent(body, "    ") + "\n"
)
(d / "dashboard-configmap.yaml").write_text(cm)
print("written", len(body), "bytes of JSON")
