# FDXF Worksheet Source Manifest

Run created: 2026-11-20 02:38:51 EST

| Document | Form | Accession | SEC source | Saved normalized text | SHA-256 |
|---|---|---|---|---|---|
| Amended registration statement | 10-12B/A | 0001104659-26-041977 | https://www.sec.gov/Archives/edgar/data/2082247/0001104659-26-041977.txt | `filings/form10a_primary_000110465926041977.normalized.txt` | `649d37373551f4a0b9b3e4a565cd07be1603426a69fe97f1e5c0a03f128a13c2` |
| Final information statement | 8-K Exhibit 99.1 | 0001104659-26-060223 | https://www.sec.gov/Archives/edgar/data/1048911/000110465926060223/tm2520565d14_ex99-1.htm | `filings/final_information_statement_000110465926060223.normalized.txt` | `ece8df5f5a1d9d6ce23f7bfc2d1c26f3631dccf3db84e5391f6c48f2c7aab29a` |
| Parent completion report | 8-K | 0001104659-26-068519 | https://www.sec.gov/Archives/edgar/data/1048911/000110465926068519/0001104659-26-068519-index.htm | `filings/fdx_completion_8k_primary_000110465926068519.normalized.txt` | `1b1f1b89f109d1a92d9c38c350b35f0069d5da2805b5471d1fea3b6431eba7e3` |
| Audited annual report | 10-K | 0001628280-26-053359 | https://www.sec.gov/Archives/edgar/data/2082247/000162828026053359/fdxf-20260531.htm | `filings/fdxf_10k_20260531_000162828026053359.normalized.txt` | `76961eec5092a81d3744c19f21c79d15caa2d42c81c370c72035b53da049e332` |
| First post-spin quarterly report | 10-Q | 0001628280-26-068246 | https://www.sec.gov/Archives/edgar/data/2082247/000162828026068246/fdxf-20260930.htm | `filings/fdxf_10q_20260930_000162828026068246.normalized.txt` | `65956a560b8ba80040c2f361552af7a05b431ebdc57c867746031b2b0061db98` |

The licensed S&P Capital IQ workbooks remain outside this run folder and outside Git. The worksheet uses only the saved reader record derived from the dated export.

## Market-data evidence

| Source | Period | Use | Saved file | SHA-256 |
|---|---|---|---|---|
| Nasdaq official historical endpoint | 2026-10-09 through 2026-11-19 | Primary close and daily volume | `evidence/nasdaq_fdxf_20261009_20261119.json` | `775762ee9ebb4dbb3b2b62dd1390269cac43bd691aef4246b6760fcf432a3581` |
| Normalized Nasdaq reader output | 30 regular trading sessions | Deterministic liquidity calculation | `official_close_volume_reader.json` | `00d9d8d22318a530e1d14b6a33323578d5a19be5f7bc22bdb2ed638c0422a99a` |
| S&P Capital IQ derived record | 2026-11-19 | Independent close cross-check | `licensed_close_reader.json` | `17f43fb9461cb49711485a85226443929e509007a1f9d3ef66e07fdabfe9c501` |
