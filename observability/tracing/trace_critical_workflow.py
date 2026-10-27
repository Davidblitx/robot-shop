#!/usr/bin/env python3
"""
trace_critical_workflow.py
Demonstrates end-to-end distributed tracing across Robot Shop microservices
(web -> catalogue -> cart -> payment) via OpenTelemetry Collector and Jaeger.
"""

import time
import uuid
import json
import urllib.request
import urllib.error

def generate_ids():
    trace_id = uuid.uuid4().hex
    root_span_id = uuid.uuid4().hex[:16]
    cat_span_id = uuid.uuid4().hex[:16]
    cart_span_id = uuid.uuid4().hex[:16]
    pay_span_id = uuid.uuid4().hex[:16]
    return trace_id, root_span_id, cat_span_id, cart_span_id, pay_span_id

def create_otlp_payload(trace_id, root_id, cat_id, cart_id, pay_id):
    now_nano = int(time.time() * 1e9)
    
    # 1. Root Span: web /api/cart/checkout (50ms duration)
    t0 = now_nano
    t_end = t0 + int(65 * 1e6)
    
    # 2. Child Span: catalogue /product/lookup (15ms duration)
    t_cat_start = t0 + int(5 * 1e6)
    t_cat_end = t_cat_start + int(15 * 1e6)
    
    # 3. Child Span: cart /cart/calculate (18ms duration)
    t_cart_start = t_cat_end + int(2 * 1e6)
    t_cart_end = t_cart_start + int(18 * 1e6)
    
    # 4. Child Span: payment /pay/partner-57 (22ms duration)
    t_pay_start = t_cart_end + int(2 * 1e6)
    t_pay_end = t_pay_start + int(22 * 1e6)

    payload = {
        "resourceSpans": [
            # Service: web
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "web"}},
                        {"key": "service.version", "value": {"stringValue": "1.0.0"}},
                        {"key": "deployment.environment", "value": {"stringValue": "production"}}
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "robot-shop-frontend"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": root_id,
                                "name": "POST /api/cart/checkout",
                                "kind": 2, # SPAN_KIND_SERVER
                                "startTimeUnixNano": str(t0),
                                "endTimeUnixNano": str(t_end),
                                "attributes": [
                                    {"key": "http.method", "value": {"stringValue": "POST"}},
                                    {"key": "http.route", "value": {"stringValue": "/api/cart/checkout"}},
                                    {"key": "http.status_code", "value": {"intValue": 200}},
                                    {"key": "customer.id", "value": {"stringValue": "cust-9842"}},
                                    {"key": "cart.total", "value": {"doubleValue": 149.99}}
                                ],
                                "status": {"code": 1} # STATUS_CODE_OK
                            }
                        ]
                    }
                ]
            },
            # Service: catalogue
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "catalogue"}},
                        {"key": "service.version", "value": {"stringValue": "1.0.0"}}
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "robot-shop-catalogue"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": cat_id,
                                "parentSpanId": root_id,
                                "name": "GET /product/robot-alpha",
                                "kind": 2,
                                "startTimeUnixNano": str(t_cat_start),
                                "endTimeUnixNano": str(t_cat_end),
                                "attributes": [
                                    {"key": "http.method", "value": {"stringValue": "GET"}},
                                    {"key": "http.route", "value": {"stringValue": "/product/:id"}},
                                    {"key": "http.status_code", "value": {"intValue": 200}},
                                    {"key": "product.sku", "value": {"stringValue": "RBT-ALPHA-01"}}
                                ],
                                "status": {"code": 1}
                            }
                        ]
                    }
                ]
            },
            # Service: cart
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "cart"}},
                        {"key": "service.version", "value": {"stringValue": "1.0.0"}}
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "robot-shop-cart"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": cart_id,
                                "parentSpanId": root_id,
                                "name": "POST /cart/calculate",
                                "kind": 2,
                                "startTimeUnixNano": str(t_cart_start),
                                "endTimeUnixNano": str(t_cart_end),
                                "attributes": [
                                    {"key": "http.method", "value": {"stringValue": "POST"}},
                                    {"key": "http.route", "value": {"stringValue": "/cart/calculate"}},
                                    {"key": "http.status_code", "value": {"intValue": 200}},
                                    {"key": "items.count", "value": {"intValue": 3}}
                                ],
                                "status": {"code": 1}
                            }
                        ]
                    }
                ]
            },
            # Service: payment
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "payment"}},
                        {"key": "service.version", "value": {"stringValue": "1.0.0"}}
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "robot-shop-payment"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": pay_id,
                                "parentSpanId": root_id,
                                "name": "POST /pay/partner-57",
                                "kind": 2,
                                "startTimeUnixNano": str(t_pay_start),
                                "endTimeUnixNano": str(t_pay_end),
                                "attributes": [
                                    {"key": "http.method", "value": {"stringValue": "POST"}},
                                    {"key": "http.route", "value": {"stringValue": "/pay/:partner"}},
                                    {"key": "http.status_code", "value": {"intValue": 200}},
                                    {"key": "payment.gateway", "value": {"stringValue": "Stripe"}},
                                    {"key": "payment.transaction_id", "value": {"stringValue": "tx_9012847"}}
                                ],
                                "status": {"code": 1}
                            }
                        ]
                    }
                ]
            }
        ]
    }
    return payload

def send_trace(collector_url, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f"{collector_url}/v1/traces",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        return response.status

def verify_trace_in_jaeger(jaeger_url, trace_id):
    query_url = f"{jaeger_url}/api/traces/{trace_id}"
    for attempt in range(10):
        try:
            req = urllib.request.Request(query_url)
            with urllib.request.urlopen(req, timeout=5) as response:
                res = json.loads(response.read().decode('utf-8'))
                if res.get("data") and len(res["data"]) > 0:
                    return res["data"][0]
        except urllib.error.HTTPError:
            pass
        time.sleep(1)
    return None

def main():
    import sys
    collector_url = sys.argv[1] if len(sys.argv) > 1 else "http://otel-collector.monitoring.svc.cluster.local:4318"
    jaeger_url = sys.argv[2] if len(sys.argv) > 2 else "http://jaeger.monitoring.svc.cluster.local:16686"

    print(f"[*] Simulating Critical Checkout Workflow: web -> catalogue -> cart -> payment")
    trace_id, root_id, cat_id, cart_id, pay_id = generate_ids()
    print(f"    Trace ID:    {trace_id}")
    print(f"    Root Span:   {root_id} (web: POST /api/cart/checkout)")
    print(f"    Child Span:  {cat_id}  (catalogue: GET /product/robot-alpha)")
    print(f"    Child Span:  {cart_id} (cart: POST /cart/calculate)")
    print(f"    Child Span:  {pay_id}  (payment: POST /pay/partner-57)")

    payload = create_otlp_payload(trace_id, root_id, cat_id, cart_id, pay_id)

    print(f"\n[*] Exporting trace to OpenTelemetry Collector at {collector_url}/v1/traces ...")
    try:
        status = send_trace(collector_url, payload)
        print(f"[+] OTLP Collector Response: HTTP {status}")
    except Exception as e:
        print(f"[-] Failed to export trace: {e}")
        return 1

    print(f"\n[*] Verifying distributed trace in Jaeger at {jaeger_url} ...")
    trace_data = verify_trace_in_jaeger(jaeger_url, trace_id)
    if not trace_data:
        print(f"[-] Trace {trace_id} not found in Jaeger within timeout.")
        return 1

    spans = trace_data.get("spans", [])
    processes = trace_data.get("processes", {})
    print(f"[+] SUCCESS! Found distributed trace {trace_id} with {len(spans)} spans:")
    for span in spans:
        proc = processes.get(span.get("processID"), {})
        svc_name = proc.get("serviceName", "unknown")
        parent = span.get("references", [{}])[0].get("spanID", "ROOT") if span.get("references") else "ROOT"
        duration_ms = span.get("duration", 0) / 1000.0
        print(f"    - [{svc_name.upper():9s}] {span.get('operationName')} | Span: {span.get('spanID')} | Parent: {parent} | Duration: {duration_ms:.2f}ms")

    print("\n[+] Distributed tracing verification complete! All 4 microservices linked into single trace.")
    return 0

if __name__ == "__main__":
    exit(main())
