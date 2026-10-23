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

Two further attributes, `REST_HOST_RATE_LIMIT_ID` and `REST_HOST_RATE_LIMIT_WEIGHT`, are the "Host pool" and
"Weight" columns below. They are used only when a host Hummingbot connector throttler is shared with the
feed (#89): one klines request then draws `Weight` from the host connector's pool named `Host pool`, so the
feed and the connector spend the same exchange budget. They are declared only when the upstream candles
constants link the klines endpoint to a pool whose id the host connector constants also define; otherwise the
defaults (`None`, weight 1) apply and the feed paces itself with `REST_RATE_LIMIT` alone.

| Adapter | Limit | Pool | Host pool | Weight | Source |
|---|---|---|---|---|---|
| aevo_perpetual | 120 / 60s | per adapter | - | 1 | `aevo_perpetual_candles` :38 |
| backpack_spot, backpack_perpetual | 6000 / 60s | `backpack` | - (connectors define no `REQUEST_WEIGHT`) | 1 | `backpack_spot_candles` :38-39 (same in perpetual) |
| binance_spot | 1200 / 60s | per adapter | `REQUEST_WEIGHT` | 1 | `binance_spot_candles` :35-36 (klines own limit, pool 6000 weight/60s is looser); connector `binance_constants.py` :42; real klines weight varies with limit |
| binance_perpetual | 600 / 60s | per adapter | `REQUEST_WEIGHT` | 1 | `binance_perpetual_candles` :35-41 (klines 1200/60s at weight 2); connector `binance_perpetual_constants.py` :75 |
| bitget_spot | 20 / 1s | per adapter | - | 1 | `bitget_spot_candles` :56 |
| bitget_perpetual | 20 / 1s | per adapter | - | 1 | `bitget_perpetual_candles` :43 |
| bitmart_perpetual | 12 / 2s | per adapter | - | 1 | `bitmart_perpetual_candles` :33 |
| btc_markets_spot | 50 / 10s | per adapter | - | 1 | `btc_markets_spot_candles` :41 |
| bybit_spot | 49 / 1s | `bybit` | `ALL` | 1 | `bybit_perpetual_candles` :34,37 (spot `bybit_spot_candles` :34 is 600/5s, looser; link :42); connector `bybit_constants.py` :102 |
| bybit_perpetual | 49 / 1s | `bybit` | `GETLimit` | 1 | `bybit_perpetual_candles` :34,37 (link :38); connector `bybit_perpetual_constants.py` :114 |
| coinbase_advanced_trade | 10 / 1s | per adapter | `PUBLIC_REST_REQUESTS` | 1 | connector `coinbase_advanced_trade_constants.py` :92,127-128,175,185,209 (no candles constants) |
| decibel_perpetual | 400 / 60s | per adapter | `DECIBEL_LIMIT` | 1 | `decibel_perpetual_candles` :51,60,62; connector `decibel_perpetual_constants.py` :75 |
| dexalot_spot | 200 / 60s | per adapter | `IP_REQUEST_WEIGHT` | 1 | `dexalot_spot_candles` :30,32 (IP pool, candles weight 1); connector `dexalot_constants.py` :67 |
| evedex_perpetual | 1200 / 60s | per adapter | `REQUEST_WEIGHT` | 1 | `evedex_perpetual_candles` :41,56,58; connector `evedex_perpetual_constants.py` :95 |
| gate_io_spot | 200 / 2s | per adapter | `PublicPoints` | 1 | `gate_io_spot_candles` :31,34,45; connector `gate_io_constants.py` :49 |
| gate_io_perpetual | 300 / 1s | per adapter | `PublicPoints` | 1 | `gate_io_perpetual_candles` :31,40,42; connector `gate_io_perpetual_constants.py` :61 |
| grvt_perpetual | 1200 / 60s | per adapter | `grvtGlobalRateLimit` | 1 | connector `grvt_perpetual_constants.py` :89,91,116,122,124 (no candles constants) |
| hyperliquid_spot, hyperliquid_perpetual | 1200 / 60s | `hyperliquid` | `All` | 1 | `hyperliquid_spot_candles` :36-37 (same in perpetual); connectors `hyperliquid_constants.py` :96, `hyperliquid_perpetual_constants.py` :119 |
| kraken_spot | 1 / 1s | per adapter | `PublicEndpointLimitID` | 1 | `kraken_spot_candles` :34-36,40-43; connector `kraken_constants.py` :80 |
| kucoin_spot | 1333 / 30s | per adapter | - (connector has no global weight pool) | 1 | `kucoin_spot_candles` :32-33,40,45 (4000 weight/30s, weight 3) |
| kucoin_perpetual | 666 / 30s | per adapter | - (connector has no global weight pool) | 1 | `kucoin_perpetual_candles` :55-56,60,65 (2000 weight/30s, weight 3) |
| lighter_spot | 60 / 60s | `lighter` | `lighter_all` | 300 | `lighter_spot_candles` :34-36,39,44; connector `lighter_constants.py` :161 |
| lighter_perpetual | 60 / 60s | `lighter` | `lighter_perpetual_all` | 300 | `lighter_perpetual_candles` :29-31,34,39; connector `lighter_perpetual_constants.py` :160 |
| mexc_spot | 20000 / 60s | per adapter | `IP_REQUEST_WEIGHT` | 1 | `mexc_spot_candles` :37,39; connector `mexc_constants.py` :43 |
| mexc_perpetual | 20 / 2s | per adapter | - | 1 | `mexc_perpetual_candles` :25 |
| okx_spot, okx_perpetual | 20 / 2s | `okx` | - | 1 | `okx_spot_candles` :43 (same in perpetual) |
| pacifica_perpetual | 10 / 60s | per adapter | `PACIFICA_LIMIT` | 12 | `pacifica_perpetual_candles` :42,45,56 (125 weight/60s, weight 12); connector `pacifica_perpetual_constants.py` :65 |
| ascend_ex_spot | framework default (5 / 1s) | per adapter | - | 1 | undocumented locally |

Notes:

- Spot and perpetual variants share a pool only when they use the same host, the same
  endpoint and identical upstream limits. Binance spot (`api.binance.com`) and USD-M futures
  (`fapi.binance.com`) have separate IP budgets. Bybit's spot and perpetual sources disagree
  (600/5s vs 49/1s) on the same endpoint, so both use the stricter 49/1s.
- Host pools are declared per variant when the ids differ (Bybit `ALL` vs `GETLimit`, Lighter
  `lighter_all` vs `lighter_perpetual_all`).
- The framework limiter still counts requests, not weight (see `rate_limiter.py`); weights are
  honoured only by the shared host throttler. 429/418 backoff and per-endpoint budgets are not modelled.
