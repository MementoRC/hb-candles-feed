# REST rate limits

Every REST call is paced by the framework limiter in `candles_feed/core/rate_limiter.py`
(sliding window, counts requests, default 5 requests/second). An adapter declares its
exchange's documented limit with two class attributes:

- `REST_RATE_LIMIT = RestRateLimit(max_requests=N, period_seconds=S)`
- `REST_RATE_LIMIT_POOL = "name"` (optional): adapters with the same pool share one limiter;
  without it each adapter class has its own pool. The first adapter to use a pool decides its limit,
  so adapters sharing a pool must declare identical limits.

Limits are taken only from the upstream Hummingbot repository (candles module `constants.py` first,
then the connector constants). The limiter counts requests, not weight, so weighted pools are
converted as `floor(pool_limit / candles_request_weight)`; where an endpoint has both its own limit
and a linked pool, the stricter effective request rate is declared. No safety margin is applied.
Adapters with no local source keep the framework default. The values are pinned by
`tests/unit/adapters/test_rest_rate_limits.py`.

Source paths are relative to the Hummingbot repository (`hummingbot/data_feed/candles_feed/<name>_candles/constants.py`
unless noted).

| Adapter | Limit | Pool | Source |
|---|---|---|---|
| aevo_perpetual | 120 / 60s | per adapter | `aevo_perpetual_candles` :38 |
| backpack_spot, backpack_perpetual | 6000 / 60s | `backpack` | `backpack_spot_candles` :38-39 (same in perpetual) |
| binance_spot | 1200 / 60s | per adapter | `binance_spot_candles` :35-36 (klines own limit, pool 6000 weight/60s is looser) |
| binance_perpetual | 600 / 60s | per adapter | `binance_perpetual_candles` :35-41 (klines 1200/60s at weight 2) |
| bitget_spot | 20 / 1s | per adapter | `bitget_spot_candles` :56 |
| bitget_perpetual | 20 / 1s | per adapter | `bitget_perpetual_candles` :43 |
| bitmart_perpetual | 12 / 2s | per adapter | `bitmart_perpetual_candles` :33 |
| btc_markets_spot | 50 / 10s | per adapter | `btc_markets_spot_candles` :41 |
| bybit_spot, bybit_perpetual | 49 / 1s | `bybit` | `bybit_perpetual_candles` :34,37 (spot `bybit_spot_candles` :34 is 600/5s, looser) |
| coinbase_advanced_trade | 10 / 1s | per adapter | connector `coinbase_advanced_trade_constants.py` :92,128,209 |
| decibel_perpetual | 400 / 60s | per adapter | `decibel_perpetual_candles` :51,60 |
| dexalot_spot | 200 / 60s | per adapter | `dexalot_spot_candles` :30,32 (IP pool, candles weight 1) |
| evedex_perpetual | 1200 / 60s | per adapter | `evedex_perpetual_candles` :41,56 |
| gate_io_spot | 200 / 2s | per adapter | `gate_io_spot_candles` :31,34,37 |
| gate_io_perpetual | 300 / 1s | per adapter | `gate_io_perpetual_candles` :28,31,36 |
| grvt_perpetual | 1200 / 60s | per adapter | connector `grvt_perpetual_constants.py` :91,122 |
| hyperliquid_spot, hyperliquid_perpetual | 1200 / 60s | `hyperliquid` | `hyperliquid_spot_candles` :36-37 (same in perpetual) |
| kraken_spot | 1 / 1s | per adapter | `kraken_spot_candles` :34-36,40-43 |
| kucoin_spot | 1333 / 30s | per adapter | `kucoin_spot_candles` :32-33,40,45 (4000 weight/30s, weight 3) |
| kucoin_perpetual | 666 / 30s | per adapter | `kucoin_perpetual_candles` :55-56,60,65 (2000 weight/30s, weight 3) |
| lighter_spot, lighter_perpetual | 60 / 60s | `lighter` | `lighter_spot_candles` :28-36 (same in perpetual :26-31) |
| mexc_spot | 20000 / 60s | per adapter | `mexc_spot_candles` :37,39 |
| mexc_perpetual | 20 / 2s | per adapter | `mexc_perpetual_candles` :25 |
| okx_spot, okx_perpetual | 20 / 2s | `okx` | `okx_spot_candles` :43 (same in perpetual) |
| pacifica_perpetual | 10 / 60s | per adapter | `pacifica_perpetual_candles` :45,56 (125 weight/60s, weight 12) |
| ascend_ex_spot | framework default (5 / 1s) | per adapter | undocumented locally |

Notes:

- Spot and perpetual variants share a pool only when they use the same host, the same
  endpoint and identical upstream limits. Binance spot (`api.binance.com`) and USD-M futures
  (`fapi.binance.com`) have separate IP budgets. Bybit's spot and perpetual sources disagree
  (600/5s vs 49/1s) on the same endpoint, so both use the stricter 49/1s.
- Request weights, 429/418 backoff and per-endpoint budgets are not modelled (see `rate_limiter.py`).
