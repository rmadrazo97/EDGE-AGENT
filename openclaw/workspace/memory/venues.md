# Venues: Binance Futures

## Exchange details

- **Type:** USDT-margined perpetual futures
- **Position mode:** ONEWAY (one position per symbol, no hedge mode)
- **Funding rate:** Every 8 hours (00:00, 08:00, 16:00 UTC)
- **Settlement:** None (perpetual contracts)

## Testnet vs mainnet

| Property | Testnet | Mainnet |
|---|---|---|
| Base URL | `https://testnet.binancefuture.com` | `https://fapi.binance.com` |
| API keys | Separate keys from testnet portal | Production Binance account |
| Liquidity | Low, fills may slip | Full market depth |
| Funding rates | May differ from mainnet | Real market rates |

**Rule:** All new features validated on testnet before mainnet. See `runbooks/go-live.md`.

## Hummingbot connector naming

- Connector name: `binance_perpetual` (mainnet) / `binance_perpetual_testnet` (testnet)
- Pair format: `BTC-USDT`, `ETH-USDT` (hyphen-separated)
- Hummingbot uses its own pair notation internally; the API client translates

## Quirks and notes

- Testnet orderbook is thin. Limit orders may not fill. Use market orders for testing.
- Funding rate can swing negative. Short positions pay funding when rate is negative.
- Binance has rate limits: 1200 request weight per minute. Hummingbot handles this internally.
- ONEWAY mode means closing a long requires a sell, not a separate short. Be explicit about `CLOSE` vs `OPEN` intent in order parameters.
