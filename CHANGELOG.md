# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.2.0](https://github.com/MementoRC/hb-candles-feed/compare/v3.1.0...v3.2.0) (2026-11-11)


### Features

* **ws:** reconnect backoff, REST catch-up and inactivity watchdog ([#180](https://github.com/MementoRC/hb-candles-feed/issues/180)) ([e30fc50](https://github.com/MementoRC/hb-candles-feed/commit/e30fc506988ae949a043c29b9fad79bc64bfc21d))

## [3.1.0](https://github.com/MementoRC/hb-candles-feed/compare/v3.0.0...v3.1.0) (2026-11-10)


### Features

* **evedex:** stream candles over the Centrifugo websocket ([#173](https://github.com/MementoRC/hb-candles-feed/issues/173)) ([d8991dc](https://github.com/MementoRC/hb-candles-feed/commit/d8991dc8f57c625cfd275cff2ffa06b00fb193ac))


### Bug Fixes

* **ci:** guard fromJSON on empty release-please pr output ([#169](https://github.com/MementoRC/hb-candles-feed/issues/169)) ([4e6e980](https://github.com/MementoRC/hb-candles-feed/commit/4e6e98024b89065cb7de1b6ad4ca8753ad03edbf))
* **evedex:** harden websocket parsing from the [#175](https://github.com/MementoRC/hb-candles-feed/issues/175) review ([#177](https://github.com/MementoRC/hb-candles-feed/issues/177)) ([1274461](https://github.com/MementoRC/hb-candles-feed/commit/127446115a7021616a191a740343006b706bee64))

## [3.0.0](https://github.com/MementoRC/hb-candles-feed/compare/v2.4.0...v3.0.0) (2026-11-05)


### ⚠ BREAKING CHANGES

* requires Python 3.12+. Drops 3.10/3.11 from CI matrix, removes py310/py311 pixi features, bumps ruff/mypy targets to py312.
* E2E tests now use aioresponses for HTTP mocking instead of URL patching This provides more robust HTTP-level interception that works regardless of import timing.

### Features

* **adapters:** declare documented per-exchange REST rate limits ([#93](https://github.com/MementoRC/hb-candles-feed/issues/93) phase 2) ([#110](https://github.com/MementoRC/hb-candles-feed/issues/110)) ([c6b4f44](https://github.com/MementoRC/hb-candles-feed/commit/c6b4f4400655f1e909c3cc2085368f9375afd9c3))
* **adapters:** seven missing candles adapters ([#81](https://github.com/MementoRC/hb-candles-feed/issues/81)) ([#91](https://github.com/MementoRC/hb-candles-feed/issues/91)) ([3e7193e](https://github.com/MementoRC/hb-candles-feed/commit/3e7193e5f2778636f0d2a1be5c49602a841a5a00))
* add hb_compat layer for hummingbot drop-in replacement ([#28](https://github.com/MementoRC/hb-candles-feed/issues/28)) ([dfb780b](https://github.com/MementoRC/hb-candles-feed/commit/dfb780bd33cf0e7a135b0a9e33298344897bc106))
* add status reporting jobs to resolve CI status check issue ([960bb95](https://github.com/MementoRC/hb-candles-feed/commit/960bb95e51faca7e4f4cf3c40f3e64c67fd2d239))
* **build:** HB_COMPILE_AUGMENTED-gated build hook for augmented DataProcessor ([#76](https://github.com/MementoRC/hb-candles-feed/issues/76)) ([#77](https://github.com/MementoRC/hb-candles-feed/issues/77)) ([fcc4f34](https://github.com/MementoRC/hb-candles-feed/commit/fcc4f343114103137641492fb867184ee6588e4f))
* **compat:** move hummingbot_network_client_adapter into hb_compat ([#69](https://github.com/MementoRC/hb-candles-feed/issues/69)) ([a9d8743](https://github.com/MementoRC/hb-candles-feed/commit/a9d8743a551f7166370c7ccc419a210367da592d))
* complete Task 10 - comprehensive integration tests for key exchange adapters ([909baee](https://github.com/MementoRC/hb-candles-feed/commit/909baeee658a4208a9ce78f26c65c724a208dd2c))
* complete Task 10.3 - Automate Code Review Assignment ([007eb16](https://github.com/MementoRC/hb-candles-feed/commit/007eb165adb9ecb1ac766441d879929b6d9fc133))
* complete Task 10.3 - Automate Code Review Assignment ([f6b607e](https://github.com/MementoRC/hb-candles-feed/commit/f6b607ea46daef001e420ca3294522fa9128cbbd))
* complete Task 10.4 - Set Up Performance Alert Notifications ([e131092](https://github.com/MementoRC/hb-candles-feed/commit/e131092e4b36f1f593dadfa5627b06a2cc8e682d))
* complete Task 10.5 - Automate Issue Triage and Labeling ([814c752](https://github.com/MementoRC/hb-candles-feed/commit/814c7523b32ba0d1fe5e03b87c36de6fe447e49e))
* complete Task 11.1 - Automate Hummingbot Integration Testing ([dd65e31](https://github.com/MementoRC/hb-candles-feed/commit/dd65e3154d4508d07b910f271e6745503b06318b))
* complete Task 11.2 - Integrate SonarCloud and Codecov for Code Quality Analysis ([f586abd](https://github.com/MementoRC/hb-candles-feed/commit/f586abdbb1e0d44ba41f6596063401e698930d3b))
* complete Task 4 - Enhance Testing Matrix ([80610ef](https://github.com/MementoRC/hb-candles-feed/commit/80610ef44c98eadca4d06486d852d6317684e670))
* complete Task 8 - Validate Network Client Adapter Delegation ([97853a6](https://github.com/MementoRC/hb-candles-feed/commit/97853a6d15e1b88c4df5909aa84a7109d2dcae6c))
* complete Task 9 - DataFrame and CandleData compatibility validation ([4374a1b](https://github.com/MementoRC/hb-candles-feed/commit/4374a1bc4b20aeed090281c6ac1fd0fbd938aa30))
* complete URL patching test isolation fixes - infrastructure ready ([d8655c9](https://github.com/MementoRC/hb-candles-feed/commit/d8655c9aa74080825770f626bb9b8aa2480e2e91))
* consolidate and optimize CI workflow for enhanced testing matrix ([0bfdc6e](https://github.com/MementoRC/hb-candles-feed/commit/0bfdc6e4f14eb37abee1b1d7ad274b4ba51a6f11))
* **core:** convert DataProcessor to augmented-pure-python (passive) + parity test ([#74](https://github.com/MementoRC/hb-candles-feed/issues/74)) ([#75](https://github.com/MementoRC/hb-candles-feed/issues/75)) ([148fcde](https://github.com/MementoRC/hb-candles-feed/commit/148fcdec0c98ceab0978462ee70d5555a84ae5a9))
* **core:** paginate get_historical_candles; keep gap data; raise on persistent fetch errors ([#83](https://github.com/MementoRC/hb-candles-feed/issues/83)) ([#105](https://github.com/MementoRC/hb-candles-feed/issues/105)) ([6bd7fc5](https://github.com/MementoRC/hb-candles-feed/commit/6bd7fc541d696b3995016c5c68e25fda4340b5eb))
* **core:** per-adapter REST rate limiting with conservative default ([#93](https://github.com/MementoRC/hb-candles-feed/issues/93)) ([#101](https://github.com/MementoRC/hb-candles-feed/issues/101)) ([9cd4add](https://github.com/MementoRC/hb-candles-feed/commit/9cd4add3cc5c8cf83967221d276c570f0537e699))
* enhance CI benchmark workflow with JSON output and artifact storage ([bd9c48d](https://github.com/MementoRC/hb-candles-feed/commit/bd9c48d5d268fe46d69d2a83137dd84fd2479268))
* extract performance benchmarks into dedicated workflow ([84402e9](https://github.com/MementoRC/hb-candles-feed/commit/84402e9305c297c0154352c090b06a572cf25107))
* fix CI workflow configuration for pixi setup ([ea0eb51](https://github.com/MementoRC/hb-candles-feed/commit/ea0eb5158866c61afb517ce96b01fa54194d9706))
* **hb_compat:** export upstream interval_to_seconds, columns, ensure_timestamp_in_seconds, UnsupportedConnectorException ([#86](https://github.com/MementoRC/hb-candles-feed/issues/86)) ([#107](https://github.com/MementoRC/hb-candles-feed/issues/107)) ([633f293](https://github.com/MementoRC/hb-candles-feed/commit/633f29391616300ab2ba203eb4e031c8dd998b8b))
* **hb_compat:** migrate StructuredLogger/JSONFormatter onto hb-logger ([#79](https://github.com/MementoRC/hb-candles-feed/issues/79)) ([35ed1f0](https://github.com/MementoRC/hb-candles-feed/commit/35ed1f039de53730f42417242c22ae6a9a0f9cd0))
* implement aioresponses-based HTTP mocking to replace URL patching (Task 5) ([481a496](https://github.com/MementoRC/hb-candles-feed/commit/481a4969a57de75c09be3253118e7357c0a5ec3e))
* implement GitHub security infrastructure - Task 2 & 3 ([9fd7298](https://github.com/MementoRC/hb-candles-feed/commit/9fd7298c430d7f4558be7348ad5733ad8002b015))
* implement Task 10 - Intelligent Automation Workflows ([0941192](https://github.com/MementoRC/hb-candles-feed/commit/0941192596d44d0fb58c9fbadfe094d1f283e4fd))
* implement Task 10.1 - Enhanced Auto-Merge for Approved Dependency Updates ([57c289c](https://github.com/MementoRC/hb-candles-feed/commit/57c289ccc5fe2596f4442761839776bf69289f45))
* implement Task 10.1 - Enhanced Auto-Merge for Approved Dependency Updates ([ca02657](https://github.com/MementoRC/hb-candles-feed/commit/ca0265776e64c88b6d0951e537d52b5f89307623))
* implement Task 10.1 - Enhanced Auto-Merge for Approved Dependency Updates ([402dd4f](https://github.com/MementoRC/hb-candles-feed/commit/402dd4fd39332b106fb50088e7a0a7aae369a447))
* implement Task 10.2 - Automate Management of Stale Issues and Pull Requests ([86216cd](https://github.com/MementoRC/hb-candles-feed/commit/86216cdb7feafa5b986b4e1149f045dcd90a083e))
* implement Task 10.2 - Enhanced Stale Issue and PR Management Automation ([d5f4fec](https://github.com/MementoRC/hb-candles-feed/commit/d5f4fec9091dada32c9736b7d8399ff26ffb3757))
* implement Task 11 - expand integration test infrastructure for all adapters ([8505637](https://github.com/MementoRC/hb-candles-feed/commit/850563752a9eade243eb1578ad120e825c9aaa62))
* implement Task 11 - External Development Tools Integration ([8bff0bb](https://github.com/MementoRC/hb-candles-feed/commit/8bff0bb0e021b08f183383092d38e1ea688d23a9))
* implement Task 11.3 - Set up Prometheus and Grafana for Application Monitoring ([894b124](https://github.com/MementoRC/hb-candles-feed/commit/894b1244e8122d514b285e74fde9033c3c8437a8))
* implement Task 11.4 - Slack/Discord CI/CD and Monitoring Notifications ([e21359f](https://github.com/MementoRC/hb-candles-feed/commit/e21359f15d974a9bcacc287bbbeada21b11e56ad))
* implement Task 11.5 - GitHub-Project Management Tool Synchronization ([13dd52e](https://github.com/MementoRC/hb-candles-feed/commit/13dd52eef50b602e2e4eadc25f7dc4eb04469b7f))
* implement Task 12 - Performance Profiling and Optimization ([0bdbe42](https://github.com/MementoRC/hb-candles-feed/commit/0bdbe42c12c5beaf5bdebdecaf62de7528e5ffe6))
* implement Task 14 - Finalize API Documentation and Integration Guides ([90ae9f4](https://github.com/MementoRC/hb-candles-feed/commit/90ae9f47b8e129df3e444c14a2d5a89d6a369807))
* implement Task 2 - Fix Mock Adapter Constructor Signatures ([457db5e](https://github.com/MementoRC/hb-candles-feed/commit/457db5e009618b7a8b2e522fffc7b78b466ad9fc))
* implement Task 4.1 - Multi-Python Version Testing in CI ([6991fc3](https://github.com/MementoRC/hb-candles-feed/commit/6991fc3db69476a100f07fa5b56a38dc5d451048))
* implement Task 4.5 - Basic Load Testing Scenarios in CI ([30405de](https://github.com/MementoRC/hb-candles-feed/commit/30405de0adf7ca06ebca1d220ce28edcb08d9d9e))
* implement Task 5 - Automated Release Management System ([15d624b](https://github.com/MementoRC/hb-candles-feed/commit/15d624b907dc4ac04f7418ea0dd7084e21f962d4))
* implement Task 6 - Fix Async Resource Cleanup and Memory Leaks in Tests ([dc44871](https://github.com/MementoRC/hb-candles-feed/commit/dc448714043ff94a0441d5878e6349223a2991c5))
* implement Task 6 - Strengthen Quality Gates ([1e96b0d](https://github.com/MementoRC/hb-candles-feed/commit/1e96b0d7be5eda6544d28e1b91205a6fcef4371b))
* implement Task 7 - Integrate GitHub Projects for Tracking ([71606ea](https://github.com/MementoRC/hb-candles-feed/commit/71606ead987781acce6f8d193922f6a59d2a64d6))
* implement Task 7 - Verify AsyncThrottler and WebAssistantsFactory Integration ([770eaaf](https://github.com/MementoRC/hb-candles-feed/commit/770eaaf8762851a99d6de7b97c925cbebcf8ab2c))
* implement Task 8 - Enhance Documentation Hub ([9ad49dc](https://github.com/MementoRC/hb-candles-feed/commit/9ad49dc08f6eff97b839456ff777c29ee6c8a46a))
* implement Task 9 - Repository Insights and Metrics ([90e7da4](https://github.com/MementoRC/hb-candles-feed/commit/90e7da4d5899a271d954550efa6af88f70906fc5))
* make Windows CI testing optional due to host environment issues ([8bdabd5](https://github.com/MementoRC/hb-candles-feed/commit/8bdabd5604b83d8c22a2da33fe93ee90bec6b7d5))
* optimize CI matrix for Hummingbot Python 3.12+ environment ([44aa0bb](https://github.com/MementoRC/hb-candles-feed/commit/44aa0bbc1a150bc4eedab51c2a97603a302f1cf1))
* **py312:** add [@override](https://github.com/override) decorators across all adapters ([#59](https://github.com/MementoRC/hb-candles-feed/issues/59)) ([3d4de62](https://github.com/MementoRC/hb-candles-feed/commit/3d4de62895a84741d7f8e1b9cde5c713c47f6acf))
* **rate-limit:** back core/rate_limiter onto hb-rate-limit v0.1.0 (spec §3) ([#115](https://github.com/MementoRC/hb-candles-feed/issues/115)) ([4123603](https://github.com/MementoRC/hb-candles-feed/commit/41236032a5c322460e81806a8af702075fb4da82))
* **rate-limit:** pool-wide 429/418 backoff honoring Retry-After ([#93](https://github.com/MementoRC/hb-candles-feed/issues/93)) ([#112](https://github.com/MementoRC/hb-candles-feed/issues/112)) ([34eef71](https://github.com/MementoRC/hb-candles-feed/commit/34eef7195ff39c475e4759ab6dfb4409461303b9))
* **rate-limit:** share the host connector's rate-limit budget ([#89](https://github.com/MementoRC/hb-candles-feed/issues/89)) ([#111](https://github.com/MementoRC/hb-candles-feed/issues/111)) ([0f2d5d4](https://github.com/MementoRC/hb-candles-feed/commit/0f2d5d4c4b9bd175cf77cd31aeed2c9f9066fc63))
* replace custom CI with ci-framework v2.5.1 reusable workflow ([57e3905](https://github.com/MementoRC/hb-candles-feed/commit/57e39051468cb4861b7652f779cfe4c1d8a57481))
* resolve import organization and whitespace lint violations (Task 4) ([adb1dca](https://github.com/MementoRC/hb-candles-feed/commit/adb1dcae3c3c2226d541f9302fd35f3e1f717192))
* separate performance benchmarks from functional CI tests ([00ba381](https://github.com/MementoRC/hb-candles-feed/commit/00ba381cee65881f24edf7c6541ef0096cb98306))


### Bug Fixes

* **adapters:** accept network_config in adapter base ([#94](https://github.com/MementoRC/hb-candles-feed/issues/94)) ([#99](https://github.com/MementoRC/hb-candles-feed/issues/99)) ([7d03994](https://github.com/MementoRC/hb-candles-feed/commit/7d0399495f2d73b1bcb0cd5f454d76e91f00542d))
* **adapters:** calendar-aware 1M/1w REST windows, drop poll_once ceil workaround ([#103](https://github.com/MementoRC/hb-candles-feed/issues/103)) ([#104](https://github.com/MementoRC/hb-candles-feed/issues/104)) ([03f382d](https://github.com/MementoRC/hb-candles-feed/commit/03f382dfe032828ef27c235e53c2d4963396ef04))
* add [@pytest](https://github.com/pytest).mark.integration to all integration test classes ([82332c1](https://github.com/MementoRC/hb-candles-feed/commit/82332c1f68fa3a9d8c0b481f8f7553fc8e0896a6))
* add CI debugging for Windows Python version issues and improve platform compatibility ([fdf0a8e](https://github.com/MementoRC/hb-candles-feed/commit/fdf0a8ed74a98422f9b731bedbe8d8fa7b86c62a))
* add development package installation to CI workflow ([d52d2fe](https://github.com/MementoRC/hb-candles-feed/commit/d52d2fe97dd36aee3c94bd02f508757127b634b9))
* add hatch build configuration to specify package directory ([d9cf436](https://github.com/MementoRC/hb-candles-feed/commit/d9cf4369627dd612625e40315c00d384a448745c))
* add missing hatch version configuration to pyproject.toml ([2022b90](https://github.com/MementoRC/hb-candles-feed/commit/2022b9097c7ec10ff0367bc1bd5415bd93d9d965))
* add production URL methods to testnet mixin test adapters ([450d31e](https://github.com/MementoRC/hb-candles-feed/commit/450d31e01d65d24b764eb2cd2366031cc8d05c7c))
* add quality-extended and quality-ci pixi environments for ci-framework ([32356cd](https://github.com/MementoRC/hb-candles-feed/commit/32356cddcd70d8fc5cb107562cd25b35470d0038))
* add robust optional imports for prometheus_client with graceful fallback ([7ecced6](https://github.com/MementoRC/hb-candles-feed/commit/7ecced63ac1a6ddc2ded343856387d194cb0715c))
* add status reporting jobs to resolve GitHub branch protection status check issue ([40ac7c0](https://github.com/MementoRC/hb-candles-feed/commit/40ac7c0222b660234356530642a55921c4c8c572))
* add type annotation for _ACTIVE_SESSIONS to resolve mypy error ([be2529d](https://github.com/MementoRC/hb-candles-feed/commit/be2529d45cc22f6b831d9250a7239dcc6a35c7fe))
* address code review feedback ([bc4cc6d](https://github.com/MementoRC/hb-candles-feed/commit/bc4cc6d78e800b59e0eff32c9cd152e2dfc891b7))
* address code review feedback ([03b026a](https://github.com/MementoRC/hb-candles-feed/commit/03b026aad81671d82de26afb450bace7e399c207))
* address sourcery review - NaN safety and test coverage ([#32](https://github.com/MementoRC/hb-candles-feed/issues/32)) ([977aa4d](https://github.com/MementoRC/hb-candles-feed/commit/977aa4dad5bbd9f049f56acbe5f630fbafe9da2c))
* AI-powered CI failure resolution - service container timeouts and test reliability ([f7c4bd1](https://github.com/MementoRC/hb-candles-feed/commit/f7c4bd1ad5b25d22f25d055e6b836aa94ed6a603))
* AI-powered CI failure resolution for PR [#10](https://github.com/MementoRC/hb-candles-feed/issues/10) ([1ef94ec](https://github.com/MementoRC/hb-candles-feed/commit/1ef94ecdfcd552cf2ed364ae8c48263a35c4b8bb))
* AI-powered CI failure resolution for PR [#10](https://github.com/MementoRC/hb-candles-feed/issues/10) ([6e4c694](https://github.com/MementoRC/hb-candles-feed/commit/6e4c694a318d9d222da3be58d14fb3c95c681217))
* AI-powered CI failure resolution for PR [#26](https://github.com/MementoRC/hb-candles-feed/issues/26) ([beab595](https://github.com/MementoRC/hb-candles-feed/commit/beab595587f8265b5e59a194c16fa04af125bb56))
* apply code formatting to integration tests ([798ff45](https://github.com/MementoRC/hb-candles-feed/commit/798ff455cc44b6fbb74461155c140d533274b636))
* apply code formatting to resolve CI quality checks ([b5e8f5b](https://github.com/MementoRC/hb-candles-feed/commit/b5e8f5b97af082fce7a6f29d79053d7f02a2635f))
* apply final code formatting for complete CI compliance ([7c3a9e0](https://github.com/MementoRC/hb-candles-feed/commit/7c3a9e0e938a3e7c7701aa7a366f1d0b58bb0be8))
* apply final formatting to task8_validation.py ([111fcdd](https://github.com/MementoRC/hb-candles-feed/commit/111fcdd3988a26cf2c994300540a140c31541ecd))
* apply ruff formatting to load testing files ([3c8bd35](https://github.com/MementoRC/hb-candles-feed/commit/3c8bd35725817ef8f9ff750fb2daae472fc4796a))
* apply ruff formatting to resolve additional CI lint failures ([f6198c8](https://github.com/MementoRC/hb-candles-feed/commit/f6198c8dc35d2d2c31a8da2a9295322445d77e61))
* apply ruff formatting to resolve CI format check failures ([52f1d0a](https://github.com/MementoRC/hb-candles-feed/commit/52f1d0a979fd21d530ae84e46a307f48c804f4c1))
* apply ruff formatting to resolve CI lint failures ([20f3ec4](https://github.com/MementoRC/hb-candles-feed/commit/20f3ec461ba24c75d51855b70104f49aae0b4f38))
* apply ruff formatting to resolve CI linting failures ([a8c8e51](https://github.com/MementoRC/hb-candles-feed/commit/a8c8e516c60ee782b415c7c2adc288f4861c5c42))
* apply ruff formatting to test_mock_server.py ([204a407](https://github.com/MementoRC/hb-candles-feed/commit/204a407231461a2f48e63daf9d7bc8c7cdc5da4e))
* bump setup-pixi from v0.8.8 to v0.9.4 in new workflows ([30e0068](https://github.com/MementoRC/hb-candles-feed/commit/30e0068751be37e85c722d9e08b0b680c09f5b6e))
* **check:** exclude live tests from default check task — they hit real exchange APIs ([#63](https://github.com/MementoRC/hb-candles-feed/issues/63)) ([8827777](https://github.com/MementoRC/hb-candles-feed/commit/8827777728ebdd79a2d9b1c6553f7fff006e00c1))
* CI resolution iteration 1 - apply consistent formatting ([1da758c](https://github.com/MementoRC/hb-candles-feed/commit/1da758c7bf2b8b5f699a09e1016fe3b8e69986cd))
* CI resolution iteration 2 - address mypy configuration issue ([4d8ec9e](https://github.com/MementoRC/hb-candles-feed/commit/4d8ec9ea65c1fe0777f465116609baf69c8fce26))
* CI resolution iteration 2 - address persistent failures ([0fe0eb1](https://github.com/MementoRC/hb-candles-feed/commit/0fe0eb155e7471def3e9bf3379887bb8c7dc11ad))
* CI resolution iteration 2 - optimize test execution for resource constraints ([894889a](https://github.com/MementoRC/hb-candles-feed/commit/894889a243dc86417b94c8cbf4daa221b0b2bd3c))
* CI resolution iteration 3 - fix repository health dashboard test ([74aec60](https://github.com/MementoRC/hb-candles-feed/commit/74aec60425f7192c3f15b8a37a4e2feaab917a3d))
* CI resolution iteration 3 - integration test stability ([8f82a3b](https://github.com/MementoRC/hb-candles-feed/commit/8f82a3ba674027a3c962fb4cb8f5b8d0f0634630))
* **ci:** remove never-running hummingbot-integration-tests workflow ([#116](https://github.com/MementoRC/hb-candles-feed/issues/116)) ([67bdfb9](https://github.com/MementoRC/hb-candles-feed/commit/67bdfb9b97596d7c607a07837403485a47bfb19b))
* **ci:** replace permissions: read-all with deny-all default ([#60](https://github.com/MementoRC/hb-candles-feed/issues/60)) ([706f7ac](https://github.com/MementoRC/hb-candles-feed/commit/706f7ac0927013ce49e61dc1a4c997eb6760d310))
* commit remaining aider formatting improvements ([6e6e489](https://github.com/MementoRC/hb-candles-feed/commit/6e6e489ca0b53f46f0eedeae43c89418b481e035))
* **compat:** empty candles_df keeps columns and dtypes ([#84](https://github.com/MementoRC/hb-candles-feed/issues/84)) ([#90](https://github.com/MementoRC/hb-candles-feed/issues/90)) ([a4d6623](https://github.com/MementoRC/hb-candles-feed/commit/a4d66239c3a9e40588da372bcc5a530a22dc4e68))
* **compat:** get_candle accepts connector ([#82](https://github.com/MementoRC/hb-candles-feed/issues/82)) ([#88](https://github.com/MementoRC/hb-candles-feed/issues/88)) ([7a69a85](https://github.com/MementoRC/hb-candles-feed/commit/7a69a85a86c81338383f83c4b1de84b3eadb5208))
* complete resolution of adapter protocol compliance test failures ([4bd2644](https://github.com/MementoRC/hb-candles-feed/commit/4bd26443594995f677fc566657f5b51feaa6cd1c))
* **core:** calendar-aware 1w/1M interval handling ([#98](https://github.com/MementoRC/hb-candles-feed/issues/98)) ([#102](https://github.com/MementoRC/hb-candles-feed/issues/102)) ([421d885](https://github.com/MementoRC/hb-candles-feed/commit/421d8856f39172e20b7382a203d913244a4fa380))
* **core:** start('auto') falls back to REST polling when WS is unsupported ([#95](https://github.com/MementoRC/hb-candles-feed/issues/95)) ([#100](https://github.com/MementoRC/hb-candles-feed/issues/100)) ([8d23498](https://github.com/MementoRC/hb-candles-feed/commit/8d234989606c8852b346b805ca31532aad40c875))
* correct ci-success job echo reference ([55c291d](https://github.com/MementoRC/hb-candles-feed/commit/55c291d4164f0cfa5fc1c5c6b10bf177a111bfac))
* correct multi-Python version testing with proper pixi environments ([9b45390](https://github.com/MementoRC/hb-candles-feed/commit/9b4539071e9d820a1e2acefc15f075b90392e8b2))
* correct OKX WebSocket subscription payload format in tests ([38ce0d4](https://github.com/MementoRC/hb-candles-feed/commit/38ce0d4d8c6698ce47177e12e793297de24bb3ab))
* correct prometheus_client dependency version specification ([40d51ea](https://github.com/MementoRC/hb-candles-feed/commit/40d51ead7d2125bb62a04c8712e1cc0108aa7a56))
* correct WebSocket state checking using websockets.protocol.State.OPEN ([c9716ea](https://github.com/MementoRC/hb-candles-feed/commit/c9716ea004f6b6ab03799da3a19972860dd9c882))
* correct XML fallback heredoc syntax in CI workflow ([3e3614b](https://github.com/MementoRC/hb-candles-feed/commit/3e3614b0ce23c5c225b14498b5509446575d9f3a))
* deduplicate CI by trimming integration-tests.yml ([a402946](https://github.com/MementoRC/hb-candles-feed/commit/a4029460419ac783d7c7e09f7dc2dcbae982bdbe))
* deduplicate CI by trimming integration-tests.yml ([6c550f7](https://github.com/MementoRC/hb-candles-feed/commit/6c550f7f038d86d3af918475eaabe1363f743c69))
* **deps:** resolve aioresponses/aiohttp 3.12+ ABI incompatibility ([#64](https://github.com/MementoRC/hb-candles-feed/issues/64)) ([8dc3584](https://github.com/MementoRC/hb-candles-feed/commit/8dc358493a03761b47dcf29b7590d68bd4495cba))
* disable cleanup-dev-files workflow until bot secrets are configured ([#27](https://github.com/MementoRC/hb-candles-feed/issues/27)) ([390bc2f](https://github.com/MementoRC/hb-candles-feed/commit/390bc2ff59c3789f0030d02aa1b03d8bbdd736c3))
* disable cleanup-dev-files workflow until bot secrets are configured ([#30](https://github.com/MementoRC/hb-candles-feed/issues/30)) ([77d534a](https://github.com/MementoRC/hb-candles-feed/commit/77d534ab7df6e19d55a7401398d13025007e93fe))
* disable mypy in pre-commit to resolve CI lint failures ([3c74ff2](https://github.com/MementoRC/hb-candles-feed/commit/3c74ff29e4a99f3bb43e9a42b6f016818e156d8a))
* enhance CI test reliability with environment-aware configuration ([8e3e760](https://github.com/MementoRC/hb-candles-feed/commit/8e3e760641bdd563d772ccf24fb7aab8b5e69a4d))
* enhance CI timeout resilience and environment-specific configuration ([fdca093](https://github.com/MementoRC/hb-candles-feed/commit/fdca0937da52d41967ce226b1e24e2caf82ebede))
* enhance cross-platform test compatibility for CI environments ([89f8a5c](https://github.com/MementoRC/hb-candles-feed/commit/89f8a5c1f90337ae8267143464757ed92a6b37b6))
* enhance Hummingbot integration tests workflow robustness for CI ([9f346d0](https://github.com/MementoRC/hb-candles-feed/commit/9f346d0dbce019023ba6f682b76a50a013df203c))
* exclude mocking resources from CI mypy checks ([207ca10](https://github.com/MementoRC/hb-candles-feed/commit/207ca10e5a345fb2aa0ee50f18b84f3fb8502a75))
* format test file to resolve CI linting failure ([0fa9bb9](https://github.com/MementoRC/hb-candles-feed/commit/0fa9bb9551a59af60821952c7b856f26a84ce9ef))
* **gate_io:** map spot candlestick columns per Gate.io v4 order ([#117](https://github.com/MementoRC/hb-candles-feed/issues/117)) ([99e519d](https://github.com/MementoRC/hb-candles-feed/commit/99e519d7448292969cd7df32df9b6405b3cc5355))
* **hb_compat:** fetch_candles parity — no store side effect, None-times ValueError, exchange-max limit ([#85](https://github.com/MementoRC/hb-candles-feed/issues/85)) ([#106](https://github.com/MementoRC/hb-candles-feed/issues/106)) ([e7db72e](https://github.com/MementoRC/hb-candles-feed/commit/e7db72e34a472e147b3b16232150c7f36936af5f))
* **hb_compat:** track start/stop tasks, safe partial-start cleanup, vectorized reset_with_dataframe ([#87](https://github.com/MementoRC/hb-candles-feed/issues/87) G14, G15) ([#108](https://github.com/MementoRC/hb-candles-feed/issues/108)) ([14678f9](https://github.com/MementoRC/hb-candles-feed/commit/14678f9084e495aad60a8a1416cb2075a96a04d0))
* improve change detection robustness in CI workflow ([ab215f4](https://github.com/MementoRC/hb-candles-feed/commit/ab215f4d8483c18dba92c89f7c1c7e8123b39e5d))
* improve CI environment compatibility for static analysis ([8cfe250](https://github.com/MementoRC/hb-candles-feed/commit/8cfe250551049ee18642aa84c50912270d078f7d))
* improve WebSocket State import for better CI compatibility ([4b01977](https://github.com/MementoRC/hb-candles-feed/commit/4b019779eddd6cda26b9391a7bba2d5aa84cc439))
* infrastructure improvements for mock adapter consistency ([54a9648](https://github.com/MementoRC/hb-candles-feed/commit/54a9648386c37cb13628f958840dec42cc1bd7ff))
* install redis-tools for CI service container health checks ([becc7d2](https://github.com/MementoRC/hb-candles-feed/commit/becc7d21625d5e1545a5906dcfdb9a92b227dd40))
* **integration:** stop candles_feed.integration importing hummingbot.core directly ([#68](https://github.com/MementoRC/hb-candles-feed/issues/68)) ([969a1e6](https://github.com/MementoRC/hb-candles-feed/commit/969a1e65ac751eaa1462c728803c668a4a202703))
* modernize Python type annotations and imports ([bce9459](https://github.com/MementoRC/hb-candles-feed/commit/bce94593fa1f744029f5ab59bdd4b7fcf076e82d))
* modernize Python type annotations for CI compliance ([1e2f0c3](https://github.com/MementoRC/hb-candles-feed/commit/1e2f0c3e88cc57f8791170acddbaff0602e05387))
* move logging statements into ImportError exception handlers ([243dd9a](https://github.com/MementoRC/hb-candles-feed/commit/243dd9a1a7f780d56b943719b7d31b2b6b9b693a))
* **rate-limit:** raise on conflicting shared-pool limits instead of first-wins ([#93](https://github.com/MementoRC/hb-candles-feed/issues/93)) ([#113](https://github.com/MementoRC/hb-candles-feed/issues/113)) ([55082d3](https://github.com/MementoRC/hb-candles-feed/commit/55082d3e7722ba7eb9e2676f4add035b910fbc72))
* reformat test_simple_mock_plugin.py to match code style ([c428ba3](https://github.com/MementoRC/hb-candles-feed/commit/c428ba35001519c558c375d77ed16f868e6f58b4))
* remove deprecated typing.Type import ([62e1a33](https://github.com/MementoRC/hb-candles-feed/commit/62e1a339003e972133adf3a1c27b4ab35f81f37f))
* remove invalid enable-release input causing CI startup_failure ([afaaf2b](https://github.com/MementoRC/hb-candles-feed/commit/afaaf2b887e242685a10e831b7093e3f9e79e274))
* remove invalid enable-release input causing CI startup_failure ([efb753b](https://github.com/MementoRC/hb-candles-feed/commit/efb753b27a42b175786ca1d261d24b90feb5889d))
* remove invalid enable-release input causing startup_failure ([da704bd](https://github.com/MementoRC/hb-candles-feed/commit/da704bd52d3741385d5d9e62159d9ce948d7486a))
* remove problematic debugging command from CI workflow ([3f9e96c](https://github.com/MementoRC/hb-candles-feed/commit/3f9e96c290195de76ad29c48c75d92cc2f599f14))
* remove tracked .pyc files that fail repository hygiene check ([24bdd2d](https://github.com/MementoRC/hb-candles-feed/commit/24bdd2dbb58b674b8e26216e0a776b8e773dfa02))
* remove unused typing imports for F401 compliance ([d2fd323](https://github.com/MementoRC/hb-candles-feed/commit/d2fd323f6e6cdcca3053fb79952a0ce02c4397f2))
* remove WebSocket echo server health check in CI ([b50d49b](https://github.com/MementoRC/hb-candles-feed/commit/b50d49b0ccf621a81ea5b7a43198fe7a151654c1))
* remove Windows platform and fix benchmark CI environment ([fd7fbc2](https://github.com/MementoRC/hb-candles-feed/commit/fd7fbc2658a8cdea88c68881c6c8cce1f7609c7e))
* remove Windows testing platform from CI matrix ([03b896b](https://github.com/MementoRC/hb-candles-feed/commit/03b896b44b9771f2ce9bdf39f503bd11f99f00c7))
* rename ci job key to avoid redundant 'CI / ci /' prefix in checks ([5b722f8](https://github.com/MementoRC/hb-candles-feed/commit/5b722f8b6ccb33f22efefe68d584ea5543c3d4c4))
* rename ci job key to avoid redundant 'CI / ci /' prefix in checks ([6a475fa](https://github.com/MementoRC/hb-candles-feed/commit/6a475faae3908f9183aa19d88140c1e823f1729d))
* resolve adapter test failures due to end_time parameter removal ([da57fa8](https://github.com/MementoRC/hb-candles-feed/commit/da57fa849ce07f6a204d1199fe51e5e1ffc17ac4))
* resolve all F401 unused import violations across test suite ([acd9d1b](https://github.com/MementoRC/hb-candles-feed/commit/acd9d1bbf0ae53bddac7c91728424233e561eacd))
* resolve all ruff linting issues across codebase ([8da7e88](https://github.com/MementoRC/hb-candles-feed/commit/8da7e881da4ff845de27a0e273821e2d1bf45854))
* resolve CI Code Quality failures - detect-secrets and pre-commit issues ([19d2de6](https://github.com/MementoRC/hb-candles-feed/commit/19d2de689ba3e0ccd750c653087119f68a8af70f))
* resolve CI code quality violations - lint style improvements ([6e1b2e4](https://github.com/MementoRC/hb-candles-feed/commit/6e1b2e412e8535293ac5e47dd3cf029cc071fdc2))
* resolve CI failures - missing NetworkConfig export and lint violations ([c0d63e1](https://github.com/MementoRC/hb-candles-feed/commit/c0d63e1a3cf98c5864c68ecdaf8118e00aafd325))
* resolve CI failures after Task 7 implementation ([d9c2533](https://github.com/MementoRC/hb-candles-feed/commit/d9c25337ff45e3f17736076d42573991412a3fd5))
* resolve CI failures and pre-commit hook issues ([d7d11cd](https://github.com/MementoRC/hb-candles-feed/commit/d7d11cda370517d75ae56394c56739ec892e7cb7))
* resolve CI failures for Bybit adapter tests ([94a279c](https://github.com/MementoRC/hb-candles-feed/commit/94a279c6c81c698f1a063defef3bc4d435dd1860))
* resolve CI failures for PR [#10](https://github.com/MementoRC/hb-candles-feed/issues/10) ([df5f586](https://github.com/MementoRC/hb-candles-feed/commit/df5f5866d6cb860425e52d2706ad4f389abffd34))
* resolve CI failures for PR [#10](https://github.com/MementoRC/hb-candles-feed/issues/10) ([07ca69f](https://github.com/MementoRC/hb-candles-feed/commit/07ca69f7edca4324a22ab65ee46dfe310441ad47))
* resolve CI failures for PR [#10](https://github.com/MementoRC/hb-candles-feed/issues/10) ([43be9e9](https://github.com/MementoRC/hb-candles-feed/commit/43be9e93cda4bca0bda0e2dd45fc76e91c5331f1))
* resolve CI failures for PR [#10](https://github.com/MementoRC/hb-candles-feed/issues/10) ([a52b071](https://github.com/MementoRC/hb-candles-feed/commit/a52b0718cc4e906f38154bbaa245726ef8524897))
* resolve CI failures for PR [#10](https://github.com/MementoRC/hb-candles-feed/issues/10) ([c89921f](https://github.com/MementoRC/hb-candles-feed/commit/c89921fef303c2c5eae2718646be56ef6efc4621))
* resolve CI failures for PR [#10](https://github.com/MementoRC/hb-candles-feed/issues/10) ([249e475](https://github.com/MementoRC/hb-candles-feed/commit/249e475379db134c4aa2aa8d613b38eb9728e022))
* resolve CI failures for repository insights and metrics tests ([4525275](https://github.com/MementoRC/hb-candles-feed/commit/452527547a6f2060749206ea1d2aed2c4afb28c8))
* resolve CI failures in code quality analysis workflow ([f194604](https://github.com/MementoRC/hb-candles-feed/commit/f194604c1d152a21273b7b73c76f3b167fcf244d))
* resolve CI failures with robust service container integration ([b7f1ad0](https://github.com/MementoRC/hb-candles-feed/commit/b7f1ad01a8f179be2e8743522b8296b409161034))
* resolve CI formatting and type checking failures ([41bc1d2](https://github.com/MementoRC/hb-candles-feed/commit/41bc1d2d3f35566aafd68ebe21ee3152fd5ff4d3))
* resolve CI formatting issues - format check now passes ([3047648](https://github.com/MementoRC/hb-candles-feed/commit/30476489017cb60885f43357f8c2de4fc06176fa))
* resolve CI lint violations ([73d1d0c](https://github.com/MementoRC/hb-candles-feed/commit/73d1d0cc4be9ec94d6fea36e9b60c5c0e7b4f7e6))
* resolve CI test failures and lint violations ([f9e275e](https://github.com/MementoRC/hb-candles-feed/commit/f9e275ee906107a81af60913101100834e409ae0))
* resolve CI test failures for multi-Python compatibility ([7a31c9f](https://github.com/MementoRC/hb-candles-feed/commit/7a31c9fea96404f0f5b28ebf9fd0c71e6c74e5dd))
* resolve CI test isolation failures ([4cae5d2](https://github.com/MementoRC/hb-candles-feed/commit/4cae5d27be4c0b20fe0337ea301596d6e7eb74c8))
* resolve CI timeout failures in service container initialization ([b04c016](https://github.com/MementoRC/hb-candles-feed/commit/b04c0169ec032a1ef38bcd8a0d392cd6640deb89))
* resolve code formatting violation in test_service_container_integration.py ([3ba700d](https://github.com/MementoRC/hb-candles-feed/commit/3ba700d6198015ad1e18eb8befa8f163f1c4ebd0))
* resolve CodeQL "no effect" warning in MonitoringProtocol ([09e3276](https://github.com/MementoRC/hb-candles-feed/commit/09e32768f473888a9fa60ef92dae922dbb9c80f0))
* resolve CodeQL failures for PR [#10](https://github.com/MementoRC/hb-candles-feed/issues/10) ([19cc836](https://github.com/MementoRC/hb-candles-feed/commit/19cc83647aca764377da38b6db8b17d352bd1fd5))
* resolve CodeQL security issues - unused imports and uninitialized variables ([2ee6bab](https://github.com/MementoRC/hb-candles-feed/commit/2ee6bab984bb2186d48bcb31255348716fbb252a))
* resolve CodeQL unreachable code warning in metrics tests ([1f0aaac](https://github.com/MementoRC/hb-candles-feed/commit/1f0aaac20178d62e5e1c4929a8f6d502b79274f7))
* resolve comprehensive mypy type checking violations ([8d452b6](https://github.com/MementoRC/hb-candles-feed/commit/8d452b662abbe880575cce29e7673f405435d227))
* resolve critical F401 lint violations and test error handling ([cce588b](https://github.com/MementoRC/hb-candles-feed/commit/cce588b85f7377fe60e736536f4b0dc6639a1183))
* resolve critical mypy type annotation errors ([2e9ccd7](https://github.com/MementoRC/hb-candles-feed/commit/2e9ccd78eb3cdf8d07420125dcfc38b7d5ffe9d9))
* resolve critical test failures - 2 of 5 tests fixed ([0b5450a](https://github.com/MementoRC/hb-candles-feed/commit/0b5450a4a8e718a1c0a3a06de6b1ef209a7150fb))
* resolve final CI type checking violations ([4747f07](https://github.com/MementoRC/hb-candles-feed/commit/4747f07e05aaa93a4903e1d2d3b0f22a9e3a4df1))
* resolve final quality violations and test failures ([9da12d4](https://github.com/MementoRC/hb-candles-feed/commit/9da12d454cc131ddd9cef2923371bcf9624f9b6c))
* resolve flaky network simulation test in CI ([181b2d5](https://github.com/MementoRC/hb-candles-feed/commit/181b2d53c532a8ed1f07f183008e5735bebd4a3b))
* resolve import ordering and formatting issues in conftest.py ([43f613b](https://github.com/MementoRC/hb-candles-feed/commit/43f613ba54feeb32f5026045f7dd5fa8a8e5ce13))
* resolve lint violations and code formatting issues ([d8a4ee7](https://github.com/MementoRC/hb-candles-feed/commit/d8a4ee7f7d55779b6f14cd3263d5a3d0dd05b604))
* resolve lint violations from CI ([ee8b4a4](https://github.com/MementoRC/hb-candles-feed/commit/ee8b4a42bfe3a816a4039b42212003b979b1cbc1))
* resolve lint violations from TaskMaster infrastructure ([f64374c](https://github.com/MementoRC/hb-candles-feed/commit/f64374c5259a237f633a3d7f51d4c59c528c9f35))
* resolve linting issues in new integration test files ([dbad5b3](https://github.com/MementoRC/hb-candles-feed/commit/dbad5b34975a847d75518515d9f03e5c84be630f))
* resolve linting issues in repository health dashboard fixes ([b8ebeb6](https://github.com/MementoRC/hb-candles-feed/commit/b8ebeb67282def189694e3071a36b7dcd05a65fe))
* resolve linting violations in metrics and profiling modules ([b1e642a](https://github.com/MementoRC/hb-candles-feed/commit/b1e642a704884c34efdb8007b19bc0dbe4090781))
* resolve linting violations in task8_validation.py and test files ([6fc3064](https://github.com/MementoRC/hb-candles-feed/commit/6fc306460a30864f3aa9f5586efbf82c9aaaa6d9))
* resolve macOS CI failure by separating Ubuntu and macOS test jobs ([a28774a](https://github.com/MementoRC/hb-candles-feed/commit/a28774ad7b7629d055a2c82875e22d2ede1bd790))
* resolve mocked adapter method signature incompatibilities ([daeac8e](https://github.com/MementoRC/hb-candles-feed/commit/daeac8eb260edda1e14ca26d26dd582b1f702dee))
* resolve MockedPlugin test failures and continue F401 cleanup ([8477528](https://github.com/MementoRC/hb-candles-feed/commit/84775285fb277e792385c76987142d60f196b67f))
* resolve MockedPlugin WebSocket subscription response format and test async iteration ([bee2d30](https://github.com/MementoRC/hb-candles-feed/commit/bee2d30fdc46b18c63f3b415b4a8de7f6535dbc7))
* resolve mypy CI failure and code formatting issues ([5691740](https://github.com/MementoRC/hb-candles-feed/commit/56917401216ed2c9b2ca7e0e982b62aec08f6a7c))
* resolve mypy type checking errors for complete CI compliance ([2b7aeb4](https://github.com/MementoRC/hb-candles-feed/commit/2b7aeb426661ac53e8782cb3fdf82310379e7d6a))
* resolve MyPy type checking errors in core notifications module ([495f220](https://github.com/MementoRC/hb-candles-feed/commit/495f2205f3037dac0a22de8980ec27a9ca5d256a))
* resolve mypy type errors in profiling module ([6106d2e](https://github.com/MementoRC/hb-candles-feed/commit/6106d2e7ebd6f028bd2ef8ee9338e043ab8bdcd2))
* resolve network strategy test failures and mock adapter limit handling ([92c40ed](https://github.com/MementoRC/hb-candles-feed/commit/92c40ed902fddf1f84d64d8b0f7fa2ef82844291))
* resolve persistent pixi CI failures by removing prometheus_client conda dependency ([fa6e61d](https://github.com/MementoRC/hb-candles-feed/commit/fa6e61dcbc29251c370bb56a64ea69263f2d929f))
* resolve pixi CI environment failures by adding prometheus_client conda dependency ([c3a8f69](https://github.com/MementoRC/hb-candles-feed/commit/c3a8f69301768ccbdc05ee78a00c035a9f17d93c))
* resolve port conflicts between service containers and unit tests ([e4eb08a](https://github.com/MementoRC/hb-candles-feed/commit/e4eb08ad3d4e8c8998f922324cd477f786da1582))
* resolve pre-commit hook issues and stage security infrastructure ([7aaccda](https://github.com/MementoRC/hb-candles-feed/commit/7aaccdaab2a9bbb81ffa0489c1f6ab3d462a9ee0))
* resolve prometheus_client dependency CI failures with optional imports ([d7db98d](https://github.com/MementoRC/hb-candles-feed/commit/d7db98dfde5b524a95f6c538a67a85038592e2a7))
* resolve prometheus_client dependency test failures ([27f2c98](https://github.com/MementoRC/hb-candles-feed/commit/27f2c9888b89bea42c322fba588c1f75056b0921))
* resolve Python 3.10 compatibility issue in test_base_adapter.py ([4f81a97](https://github.com/MementoRC/hb-candles-feed/commit/4f81a9777aaf8571cc465c6277d4f58542045499))
* resolve Python indentation error in benchmark CI script ([8f41077](https://github.com/MementoRC/hb-candles-feed/commit/8f410778cefba3025e259cab9c505fe18e61e1ec))
* resolve Python script indentation error in benchmark summary ([caa3418](https://github.com/MementoRC/hb-candles-feed/commit/caa34183e1a67afb5d7e9be619c0d4f26d2252e5))
* resolve quality validation failures and YAML corruption ([73c964d](https://github.com/MementoRC/hb-candles-feed/commit/73c964d701f6dd3288c64e4b9573ca98907a4518))
* resolve remaining adapter protocol compliance test failures ([86deae5](https://github.com/MementoRC/hb-candles-feed/commit/86deae5580348815f23ae7f91b81efc0f25d7b03))
* resolve remaining CodeQL failures - proper __init__ and try/finally pattern ([a243db7](https://github.com/MementoRC/hb-candles-feed/commit/a243db77830480788728bf3d218acdb9f648a1bc))
* resolve remaining lint and formatting issues for CI ([9bd9e25](https://github.com/MementoRC/hb-candles-feed/commit/9bd9e25aa944798296ef003927de65e00a321fe1))
* resolve repository health dashboard integration test failures ([419f117](https://github.com/MementoRC/hb-candles-feed/commit/419f117b128026e9e7eddc48bed50771f28e9d73))
* resolve ruff formatting issues and Python syntax error in CI workflow ([c440972](https://github.com/MementoRC/hb-candles-feed/commit/c4409721822e2654aa2be2858e509c66e7b93d5c))
* resolve shell parsing error in CI debugging command ([d4bc599](https://github.com/MementoRC/hb-candles-feed/commit/d4bc5994577e103e59ad6287cbdc54ee501c733a))
* resolve significant F401 unused import violations ([2a14730](https://github.com/MementoRC/hb-candles-feed/commit/2a147303ae499a90fd6875ccc6f9d900da93223c))
* resolve test isolation and null reference issues ([8ae1d13](https://github.com/MementoRC/hb-candles-feed/commit/8ae1d13e932ff865c415a351ba8e0d5ade407de7))
* resolve test isolation issues from Task 8 infrastructure changes ([a045a39](https://github.com/MementoRC/hb-candles-feed/commit/a045a3908275e5d7f82e0ab706202faa6eaae543))
* resolve URL patching pollution between integration and unit tests ([1742b63](https://github.com/MementoRC/hb-candles-feed/commit/1742b630d241aa8f0e958bf5e4264cb9708e59be))
* resolve URL patching pollution in integration tests that was breaking CI ([3965724](https://github.com/MementoRC/hb-candles-feed/commit/39657245f3b8263503018a0a18946533a2d780db))
* resolve WebSocket API compatibility issues in service container tests ([c3c735a](https://github.com/MementoRC/hb-candles-feed/commit/c3c735aac475d59792ff12c0a9be36a94310edb0))
* resolve WebSocket ClientConnection AttributeError in service container tests ([c202ab1](https://github.com/MementoRC/hb-candles-feed/commit/c202ab1806bb43f8eefa133cd2d5a49f2c36dd03))
* resolve WebSocket ClientConnection AttributeError in service container tests ([d6a32d6](https://github.com/MementoRC/hb-candles-feed/commit/d6a32d6c1d87fe57889a46860563d0dfad3298c2))
* resolve WebSocket echo server health check in CI ([5eebf17](https://github.com/MementoRC/hb-candles-feed/commit/5eebf1709edcfd1fa1dde2cbe8948b12865b9c6e))
* resolve YAML syntax error in CI workflow ([9b34702](https://github.com/MementoRC/hb-candles-feed/commit/9b34702d095c2a9b9c706d96a911559645f0fe3c))
* restore proper prometheus_client dependency using conda-forge ([a604bab](https://github.com/MementoRC/hb-candles-feed/commit/a604babc05ee99bfb6d63533a8c65b75ef6731a6))
* simplify CI workflow to use pixi exclusively ([8e9e6fc](https://github.com/MementoRC/hb-candles-feed/commit/8e9e6fc10447947b236698925a6b44f65718613c))
* temporarily disable integration tests to unblock CI ([25f864b](https://github.com/MementoRC/hb-candles-feed/commit/25f864b9c1f35b5daefc5557b9994df770f12c18))
* **test:** benchmark memory assertions measure delta ([#92](https://github.com/MementoRC/hb-candles-feed/issues/92)) ([44a7ac2](https://github.com/MementoRC/hb-candles-feed/commit/44a7ac2a5befe63918c8675a170280ea2920739f))
* **test:** mark TestEnhancedDependencyManagement as slow, exclude from check ([#65](https://github.com/MementoRC/hb-candles-feed/issues/65)) ([f9b36a0](https://github.com/MementoRC/hb-candles-feed/commit/f9b36a03ab3d8308b84f02e2c4155b640b1836bf))
* update codecov action parameter from 'file' to 'files' in CI workflow ([2ea1376](https://github.com/MementoRC/hb-candles-feed/commit/2ea1376d207fa7e50c8db9b8264d0aa6d0a7e507))
* update pixi lock file for CI compatibility ([80615dc](https://github.com/MementoRC/hb-candles-feed/commit/80615dc4b0b269df50964b084e81e039f6393abb))
* update pixi.lock with ci environment dependencies ([c153fde](https://github.com/MementoRC/hb-candles-feed/commit/c153fde98246be477d10c6459a149917eb96154e))
* update pixi.lock with multi-Python environment definitions ([942a40f](https://github.com/MementoRC/hb-candles-feed/commit/942a40f19c0622f6ec6236821f54ab098b359bdc))
* update TestAdapter classes to use abstract method signatures ([65e75df](https://github.com/MementoRC/hb-candles-feed/commit/65e75dfedd42039febf23d96252979cee30e5704))


### Dependencies

* **deps:** update aiohttp requirement ([#67](https://github.com/MementoRC/hb-candles-feed/issues/67)) ([9be1de1](https://github.com/MementoRC/hb-candles-feed/commit/9be1de1dca789e4e90e23cd4458f2621f20270be))
* **deps:** update aiohttp requirement ([#73](https://github.com/MementoRC/hb-candles-feed/issues/73)) ([ac8746d](https://github.com/MementoRC/hb-candles-feed/commit/ac8746d7555dfbf3093d8b5504c0b041a03c1309))


### Miscellaneous

* bump Python floor to &gt;=3.12 ([#58](https://github.com/MementoRC/hb-candles-feed/issues/58)) ([39d3bb6](https://github.com/MementoRC/hb-candles-feed/commit/39d3bb6d0d859b15f0838c32ac9806ed23cb4e39))

## [Unreleased]

### Added
- Automated release management system with semantic versioning
- Comprehensive CI/CD pipeline with multi-platform testing
- PyPI trusted publishing integration
- Automated changelog generation from conventional commits
- TaskMaster integration for release notes

### Changed
- Enhanced release workflow with automated version detection
- Improved package verification and testing procedures

## [2.4.0] - 2025-06-11

### Added
- GitHub Security Infrastructure implementation
- Enhanced testing matrix with comprehensive coverage
- Improved CI workflow with better change detection
- Consolidated GitHub Actions workflow optimization

### Fixed
- CI formatting issues resolved
- macOS CI failure separated from Ubuntu test jobs
- Change detection robustness improved

### Infrastructure
- Task 1: Implement comprehensive GitHub security infrastructure
- Task 2: Enhanced dependency management system
- Task 3: Monitoring and alerting system integration
- Task 4: Enhanced testing matrix with load testing capabilities
- Task 5: Automated release management system

---

*This changelog is automatically generated and maintained by our release automation system.*
