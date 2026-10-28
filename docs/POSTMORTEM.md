# Postmortem: Payment service outage (self-run drill)

Date: 2026-10-28. Blameless format. This was a deliberate drill run by me on my own cluster to test alerting, the runbook and recovery. It was not a production incident.

## Summary

The payment deployment was scaled to zero replicas on purpose. The `RobotShopPaymentAvailabilitySLOBreached` alert fired in Slack with a link to the runbook. I restored the service by scaling back to one replica. Checkout was unavailable for about 6 minutes 53 seconds.

## Impact

- Checkout (payment) was unavailable. Browsing the shop kept working.
- About 3.2% of the 30-day payment error budget was used (6.9 minutes out of 216).

## Timeline (local time, 2026-10-28)

| Time | Event |
|---|---|
| 15:39:35 | Fault injected: `kubectl scale deploy/payment -n robot-shop --replicas=0` |
| 15:40:48 | Mitigation started, 1m13s after injection: payment scaled back to 1 replica |
| about 15:41 | `RobotShopPaymentAvailabilitySLOBreached (firing)` arrived in Slack with the runbook link |
| 15:46:28 | `kubectl rollout status` reported payment rolled out and ready |
| after 15:46 | The `(resolved)` notification arrived in Slack |

## Detection

The alert fires when no ready payment pod exists for 30 seconds. It arrived in Slack about 90 seconds after the fault. Because I started mitigation before it arrived, the alert did not drive the response in this drill. In a real incident the detection time would add to the outage.

## Root cause

I scaled the payment deployment to zero replicas. I did not run the runbook's diagnosis steps (`kubectl describe deploy/payment`, events, logs) because the cause was already known. In a real incident, `kubectl get pods` would show no payment pod, and `kubectl describe deploy/payment` would show zero desired replicas and the reason.

## Resolution

Mitigate first: scale payment to 1 replica and wait for the rollout. Rollback with Helm was not needed because the change was made with `kubectl` and was not a release.

## What went well

- The alert fired and resolved correctly, and the Slack message carried a working runbook link.
- The runbook gave a clear first action (restart or scale).
- Other services stayed up, and the dashboard showed the payment pod count dropping to 0.

## What went wrong

- Recovery took 5m40s after the scale-up, which is long for a single pod.
- Payment runs as a single replica, so any pod loss means a full outage.

## Action items

| Action | Why |
|---|---|
| Run two payment replicas | Removes the single point of failure (needs spare node capacity) |
| Add a readiness probe and a startup probe to payment | Readiness would then reflect real health, and startup time would be measurable |
| Add burn-rate alerts | Detect budget burn earlier than a hard readiness failure |
| Shorten the alert delay (30s `for`, 10s group wait) if faster detection is needed | Detection took about 90 seconds |

## Baseline note

The payment service logs `'NoneType' object is not iterable` about 1,270 times an hour while healthy, because of the load generator. These log errors are not part of this incident.
