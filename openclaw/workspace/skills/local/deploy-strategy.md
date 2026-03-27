# Skill: Deploy Strategy

## Description

Start or stop agent processes (analyst, trader, reporter) with specific configuration.

## When to use

- Operator asks to "start trading", "stop the analyst", "restart the trader"
- Part of bootstrap or go-live procedures

## Steps

### Start agents

1. Verify infrastructure is healthy: `make smoke`
2. Start the requested agent process:
   - Analyst: `make analyst-once` (single cycle) or continuous mode
   - Trader: `make trader-once` (single cycle) or continuous mode
   - Reporter: `make reporter`
3. Confirm the process started by checking logs

### Stop agents

1. Identify the running process
2. Send graceful shutdown signal
3. Verify the process has stopped
4. Report final state (any open positions remain, stops stay active on exchange)

## Parameters

| Parameter | Required | Description |
|---|---|---|
| agent | yes | Which agent: `analyst`, `trader`, `reporter`, or `all` |
| action | yes | `start` or `stop` |
| mode | no | `once` (single cycle) or `continuous` (default: `once`) |

## Safety

- Stopping the trader does NOT close open positions. Stops remain active on the exchange.
- To close positions and stop, use the "Kill everything" command instead.
- Always run `make smoke` before starting agents to verify infrastructure health.
