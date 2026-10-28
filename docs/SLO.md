# SLO and Error Budget Policy: Robot Shop

Scope: the **payment** (checkout) and **web** (storefront) services in the `robot-shop` namespace.

## SLI and SLO

| Service | SLI (availability) | SLO over 30 days | Error budget |
|---|---|---|---|
| Payment | Share of time at least one payment pod is ready (`kube_pod_status_ready`) | 99.5% | 216 minutes (3h 36m) |
| Web | Share of successful HTTP probes against the storefront (`probe_success`) | 99.0% | 432 minutes (7h 12m) |

Budget maths: 30 days = 43,200 minutes. 0.5% = 216 minutes. 1.0% = 432 minutes.

Web SLI query: `avg_over_time(probe_success{job=~"probe/.*robot-shop-web"}[30d])`

## Error budget policy

| Budget remaining | What we do |
|---|---|
| More than 50% | Normal releases. |
| 50% to 0% | Only low-risk changes. Every incident gets a review. |
| Exhausted | Feature deploys stop. Only reliability fixes ship until the budget recovers. |

- Any single incident that uses more than 20% of a budget gets a blameless postmortem within two working days.
- Rollback (`helm rollback robot-shop <revision>`) is always allowed.

## Alerting

- `RobotShopPaymentAvailabilitySLOBreached` and `RobotShopWebAvailabilitySLOBreached` fire when no ready pod has existed for 30 seconds. `RobotShopHighCrashLoopRate` is a warning.
- Alerts go to the Slack `#alerts` channel through Alertmanager. Each alert carries a `runbook_url` that points to `RUNBOOK.md`.
- Burn-rate alerts are a possible improvement but are not implemented.

## Measurement and limits

- The dashboard "Robot Shop: Requests, Errors, Latency" shows availability, error ratio, latency and throughput.
- Robot Shop's services expose no request or latency metrics, so the web SLI comes from an external blackbox probe and the payment SLI from pod readiness. These are proxies for real user requests, not a measure of them.
- The payment service logs `'NoneType' object is not iterable` roughly 1,270 times an hour under the load generator while healthy. Log errors are therefore not used as an SLI.

## Drill result

<fill in after the drill: outage start, end, duration in minutes, and the percentage of the payment error budget used>
