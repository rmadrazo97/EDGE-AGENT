# Runbook: Incident Response

What to do when something goes wrong.

## Severity levels

| Level | Definition | Response time |
|---|---|---|
| Critical | Uncontrolled loss, positions stuck, system unresponsive | Immediate |
| High | Unexpected trades, policy bypass, API errors on live | Within 15 minutes |
| Medium | Missed signals, delayed notifications, testnet issues | Within 1 hour |
| Low | Cosmetic issues, non-blocking warnings | Next session |

## Immediate actions (Critical / High)

### 1. Pause trading

```
Tell OpenClaw: "Pause trading"
```

Or manually set `trading_enabled: false` in `configs/risk/policy.yml`.

### 2. Check open positions

```
Tell OpenClaw: "Show positions"
```

Or check Binance directly via the exchange UI.

### 3. Close positions if needed

```
Tell OpenClaw: "Kill everything"
```

Requires confirmation. If OpenClaw is unresponsive, close positions manually on Binance.

### 4. Check logs

```bash
# Policy audit log
tail -50 runtime/audit/policy.jsonl

# Analyst signals
tail -20 runtime/signals/analyst.jsonl

# Application logs
tail -100 runtime/logs/edge-agent.log
```

### 5. Check infrastructure

```bash
make smoke
```

If services are down:

```bash
make down
make up
make smoke
```

## Post-incident

1. Document the incident in `memory/incidents.md` using the template
2. Identify root cause
3. Add a test case that would have caught it
4. Update runbooks if the response process was unclear
5. Resume trading only after the fix is verified on testnet
