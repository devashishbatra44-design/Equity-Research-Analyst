# Market Data Method

Status: approved for this FDXF worksheet run

## Primary source

- Provider: Nasdaq official historical endpoint.
- Instrument: FDXF.
- Window: 30 regular trading sessions from October 9, 2026 through November 19, 2026.
- Fields: regular close and daily share volume.
- Use: November 19 official close and median daily dollar volume.
- Saved derived summary: `market_summary.json`.
- Raw responses and daily close lists remain outside the repository.
- Endpoint: https://api.nasdaq.com/api/quote/FDXF/historical?assetclass=stocks&fromdate=2026-10-09&todate=2026-11-19&limit=5000

## Cross-check

- Provider: S&P Capital IQ licensed local export.
- As-of date: November 19, 2026.
- Close: 126.58 USD per share.
- Result: The Capital IQ close equals the Nasdaq close for November 19, 2026.
- Limitation: The supplied Capital IQ workbooks do not contain a daily volume series.

## Human approval

- Approved by: Devashish Batra.
- Approved at: November 20, 2026 at 7:39:18 PM EST.
- Approval record: Devashish Batra wrote, `okay lets go ahead with Nasdaq as the primary source`.
- Scope: This approval changes the market-data source for this worksheet run. It does not change the frozen valuation, liquidity threshold, persona, or conviction rules.

Yahoo Finance was not used.
