# Robot Shop Runbook

Application namespace: `robot-shop`. Helm release: `robot-shop`. Monitoring namespace: `monitoring`.

Rule for every alert: mitigate first, then find the root cause.

## RobotShopPaymentAvailabilitySLOBreached

**Meaning:** no payment pod has been ready for 30 seconds, so checkout is failing and the 99.5% availability SLO error budget is burning.

**Impact:** customers cannot pay. Browsing still works.

**Mitigate first**
1. `kubectl get pods -n robot-shop | grep payment`
2. If the pod is missing or not ready: `kubectl rollout restart deploy/payment -n robot-shop`
3. If the problem began after a deploy: `helm history robot-shop`, then `helm rollback robot-shop <last good revision>`

**Investigate**
- `kubectl describe deploy/payment -n robot-shop`
- `kubectl get events -n robot-shop --sort-by=.lastTimestamp | tail -15`
- `kubectl logs deploy/payment -n robot-shop --tail=100`
- Payment depends on rabbitmq, cart and user, so check `kubectl get pods -n robot-shop`
- Known noise: repeated `'NoneType' object is not iterable` errors come from the load generator and appear when the service is healthy. They are not the incident.

**Done when:** payment shows `1/1 Running` and the alert resolves.

## RobotShopWebAvailabilitySLOBreached

**Meaning:** no web pod has been ready for 30 seconds, so the storefront is unreachable and the 99.0% availability SLO error budget is burning.

**Impact:** all customer traffic fails.

**Mitigate first**
1. `kubectl get pods -n robot-shop | grep web`
2. `kubectl rollout restart deploy/web -n robot-shop`
3. If the problem began after a deploy: `helm rollback robot-shop <last good revision>`

**Investigate**
- `kubectl logs deploy/web -n robot-shop --tail=100`
- `kubectl describe deploy/web -n robot-shop`
- `kubectl get svc web -n robot-shop` (the load balancer address should be present)

**Done when:** web shows `1/1 Running`, the shop page loads, and the alert resolves.

## RobotShopHighCrashLoopRate

**Meaning:** a pod in `robot-shop` restarted more than once a minute over five minutes.

**Mitigate first**
1. `kubectl get pods -n robot-shop` and find the pod with a high RESTARTS count
2. If it began after a deploy: `helm rollback robot-shop <last good revision>`

**Investigate**
- `kubectl logs <pod> -n robot-shop --previous`
- `kubectl describe pod <pod> -n robot-shop` (look for OOMKilled, failed probes, image errors)
- Check memory limits and recent changes in `helm history robot-shop`

**Done when:** restarts stop increasing and the alert resolves.
