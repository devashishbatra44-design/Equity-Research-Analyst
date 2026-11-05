# COSTCO WHOLESALE CORP /NEW (COST) — filings read: 10-K accession 0000909832-26-000093; 10-Q accession 0000909832-26-000051; 8-K accession 0000909832-26-000084

## Verifier marks

Code-checked claims: 11. Wrong: 0. Unsupported: 0.

| Claim | Report said | Filing says | Mark | Evidence |
|---|---:|---:|---|---|
| 1. Total revenue, latest fiscal year | 3.03154e+11 | $303.154 billion | Correct | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax; period 2026-08-30; accession 0000909832-26-000093 |
| 2. Revenue growth versus prior year | 10.14 | 10.1437% | Correct | (303154000000 - 275235000000) / 275235000000 |
| 3. Operating income and operating margin | 1.1685e+10, 3.85 | $11.685 billion; 3.8545% | Correct | us-gaap:OperatingIncomeLoss; 11685000000 / 303154000000 |
| 4. Net income attributable to the company | 9.226e+09 | $9.226 billion | Correct | us-gaap:NetIncomeLoss; period 2026-08-30 |
| 5. Diluted earnings per share, GAAP | 20.76 | $20.76 | Correct | us-gaap:EarningsPerShareDiluted; period 2026-08-30 |
| 6. Return on average equity | 28.4 | 28.4021% | Correct | 9226000000 / ((35803000000 + 29164000000) / 2) |
| 7. Debt to equity, including current debt | 0.17 | 0.1721 | Correct | (3914000000 + 2248000000) / 35803000000 |
| 8. Free cash flow | 9.382e+09 | $9.382 billion | Correct | 15817000000 - 6435000000 |
| 9. Latest-quarter revenue | 9.5723e+10 | $95.723 billion | Correct | Total revenue \| 95,723 \| 86,156 \| 303,154 \| 275,235 |
| 10. Quarter revenue growth versus the same quarter last year | 11.1 | 11.1043% | Correct | (9.5723e+10 - 8.6156e+10) / 8.6156e+10 |
| 11. Quarter diluted EPS, GAAP | 6.75 | $6.75 | Correct | Net income for the fourth quarter was $2.998 billion, $6.75 per diluted share, compared to $2.610 billion, $5.87 per diluted share, last year. This year's fourth quarter was positively impacted by a non-recurring benefit of $0.15 per diluted share from IEEPA tariff refunds received in the quarter, less partial reinvestment of those refunds in increased member values. Net income for the fiscal year was $9.226 billion, $20.76 per diluted share, compared to $8.099 billion, $18.21 per diluted share, last year. |

### Model definition review

- **Correct — 1. Annual Total Revenue:** The saved XBRL fact for `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` confirms a value of $303,154,000,000 for the period ending 2026-08-30.
- **Correct — 2. Annual Revenue Growth:** The calculation (303,154 - 275,235) / 275,235 correctly yields 10.14% using the current and prior year revenue values from the saved facts.
- **Correct — 3. Annual Operating Income:** The saved XBRL fact for `us-gaap:OperatingIncomeLoss` confirms a value of $11,685,000,000 for the period ending 2026-08-30.
- **Correct — 4. Annual Operating Margin:** The calculation 11,685 / 303,154 correctly yields 3.85% using the operating income and total revenue values from the saved facts.
- **Correct — 5. Annual Attributable Net Income:** The saved XBRL fact for `us-gaap:NetIncomeLoss` confirms a value of $9,226,000,000 for the period ending 2026-08-30.
- **Correct — 6. Annual GAAP Diluted EPS:** The saved XBRL fact for `us-gaap:EarningsPerShareDiluted` confirms a value of $20.76 for the period ending 2026-08-30.
- **Correct — 7. Return on Average Equity:** The calculation 9,226 / ((35,803 + 29,164) / 2) correctly yields 28.40% using the net income and stockholders' equity values from the saved facts.
- **Correct — 8. Debt to Equity (Including Current Debt):** The calculation (3,914 + 2,248) / 35,803 correctly yields 0.17 using the long-term debt, current portion of long-term debt, and stockholders' equity values from the saved facts.
- **Correct — 9. Free Cash Flow:** The calculation 15,817 - 6,435 correctly yields $9,382 million using the net cash provided by operating activities and additions to property and equipment values from the saved facts.
- **Correct — 10. Quarter Revenue:** The cited filing line from exhibit-99-1.txt:39 explicitly states 'Total revenue | 95,723' for the 16 weeks ended August 30, 2026.
- **Correct — 11. Quarter GAAP Diluted EPS:** The cited filing line from exhibit-99-1.txt:20 explicitly states '$6.75 per diluted share' for the fourth quarter.
- **Correct — 12. Quarter Revenue Growth:** The calculation (95,723 - 86,156) / 86,156 correctly yields 11.10% using the current and prior year quarter revenue values from the cited filing line.
- **Correct — 13. FY-EPS P/E:** The calculation 992.13 / 20.76 correctly yields 47.79 using the provided share price and the FY2026 diluted EPS from the saved facts.
- **Correct — Walmart Inc. (WMT) Operating Margin:** The calculation 29,825 / 713,163 correctly yields 4.18% using the provided operating income and total revenues values.
- **Correct — Target Corp (TGT) Operating Margin:** The calculation 5,117 / 104,780 correctly yields 4.88% using the provided operating income and net sales values.
- **Correct — BJ's Wholesale Club Holdings, Inc. (BJ) Operating Margin:** The calculation 816.604 / 21,457.274 correctly yields 3.81% using the provided operating income and total revenues values.

# Run time: 2026-11-02T23:49:54.501748-05:00

# Overview

Costco operates membership warehouses and e-commerce sites. The company began operations in 1983. "We are principally engaged in the operation of membership warehouses in the United States (U.S.) and Puerto Rico, Canada, Mexico, Japan, the United Kingdom (U.K.), Korea, Australia, Taiwan, China, Spain, France, Sweden, Iceland, and New Zealand." (10-k.txt:721). The company operated 939 warehouses worldwide at August 30, 2026. (10-k.txt:721).

The business model relies on low prices and limited product selection. "We operate membership warehouses and e-commerce sites based on the concept that offering low prices on a limited selection of nationally-branded and private-label products in a wide range of categories will produce high sales volumes and rapid inventory turnover." (10-k.txt:724). The company carries less than 4,000 active stock keeping units (SKUs) per warehouse. (10-k.txt:731).

Membership fees drive profitability. "The membership format is integral to our business and profitability." (10-k.txt:1018). The annual fee is $65 in the U.S. (10-k.txt:760). Paid members totaled 84,100,000 at the end of 2026. (10-k.txt:763). The worldwide renewal rate was 89.8% at the end of 2026. (10-k.txt:770).

Fiscal year 2026 net sales increased 10% to $297,247 million. (10-k.txt:1032). Net income increased 14% to $9,226 million. (10-k.txt:1044). The company opened 28 new warehouses in 2026. (10-k.txt:1030).

# Market Positioning and Growth Outlook

Costco competes against global, national, and regional wholesalers and retailers. "Net sales growth and gross margins are also impacted by competition, which is vigorous and widespread, across a wide range of global, national, and regional wholesalers and retailers, including those with e-commerce operations." (10-k.txt:1010). The company seeks to maintain a perception of "pricing authority." (10-k.txt:1011).

Comparable sales growth is a key driver. "We believe that the most important driver of our profitability is increasing net sales, particularly comparable sales." (10-k.txt:1010). Total company comparable sales increased 8.4% for the 52 weeks ended August 30, 2026. (exhibit-99-1.txt:17). Digitally-enabled comparable sales increased 20.9% for the 52 weeks ended August 30, 2026. (exhibit-99-1.txt:18).

International markets show higher growth rates. "Our rate of square footage growth is generally higher in many of our international markets, due to the smaller base in those markets, and we expect that to continue." (10-k.txt:1017). Other International comparable sales increased 9.8% for the 52 weeks ended August 30, 2026. (exhibit-99-1.txt:16).

The company leverages SG&A expenses through sales growth. "The higher our comparable sales exclusive of these items, the more we can leverage our selling, general and administrative (SG&A) expenses, reducing them as a percentage of sales and enhancing profitability." (10-k.txt:1010). SG&A expenses as a percentage of net sales decreased 10 basis points in 2026. (10-k.txt:1040).

## Valuation Insights

**1. Annual Total Revenue**
Costco reported annual total revenue of $303,154 million for the fiscal year ended August 30, 2026.
*   **Filing:** 10-K (Accession 0000909832-26-000093)
*   **Period:** FY2026 (2025-09-01 to 2026-08-30)
*   **Unit:** USD
*   **XBRL Tag:** `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`
*   **Filing Line:** "Total revenue"

**2. Annual Revenue Growth**
Annual revenue growth was 10.14%.
*   **Formula:** (303,154,000,000 - 275,235,000,000) / 275,235,000,000
*   **Inputs:** Current revenue $303,154 million; Prior revenue $275,235 million.
*   **Source:** Code-supplied calculation.

**3. Annual Operating Income**
Costco reported annual operating income of $11,685 million for the fiscal year ended August 30, 2026.
*   **Filing:** 10-K (Accession 0000909832-26-000093)
*   **Period:** FY2026 (2025-09-01 to 2026-08-30)
*   **Unit:** USD
*   **XBRL Tag:** `us-gaap:OperatingIncomeLoss`
*   **Filing Line:** "Operating income"

**4. Annual Operating Margin**
Annual operating margin was 3.85%.
*   **Formula:** 11,685,000,000 / 303,154,000,000
*   **Inputs:** Operating income $11,685 million; Total revenue $303,154 million.
*   **Denominator:** The denominator is the company-wide "Total revenue" line, not "Net sales."
*   **Source:** Code-supplied calculation.

**5. Annual Attributable Net Income**
Costco reported annual net income of $9,226 million for the fiscal year ended August 30, 2026.
*   **Filing:** 10-K (Accession 0000909832-26-000093)
*   **Period:** FY2026 (2025-09-01 to 2026-08-30)
*   **Unit:** USD
*   **XBRL Tag:** `us-gaap:NetIncomeLoss`
*   **Filing Line:** "NET INCOME"

**6. Annual GAAP Diluted EPS**
Costco reported annual GAAP diluted earnings per share of $20.76 for the fiscal year ended August 30, 2026.
*   **Filing:** 10-K (Accession 0000909832-26-000093)
*   **Period:** FY2026 (2025-09-01 to 2026-08-30)
*   **Unit:** USD/share
*   **XBRL Tag:** `us-gaap:EarningsPerShareDiluted`
*   **Filing Line:** "Diluted"

**7. Return on Average Equity**
Return on average equity was 28.40%.
*   **Formula:** 9,226,000,000 / ((35,803,000,000 + 29,164,000,000) / 2)
*   **Inputs:** Net income $9,226 million; Current equity $35,803 million; Prior equity $29,164 million.
*   **Source:** Code-supplied calculation.

**8. Debt to Equity (Including Current Debt)**
Debt to equity was 0.17.
*   **Formula:** (3,914,000,000 + 2,248,000,000) / 35,803,000,000
*   **Inputs:** Long-term debt $3,914 million; Current portion of long-term debt $2,248 million; Stockholders' equity $35,803 million.
*   **Source:** Code-supplied calculation.

**9. Free Cash Flow**
Free cash flow was $9,382 million.
*   **Formula:** 15,817,000,000 - 6,435,000,000
*   **Inputs:** Net cash provided by operating activities $15,817 million; Additions to property and equipment $6,435 million.
*   **Source:** Code-supplied calculation.

**10. Quarter Revenue**
Costco reported quarter total revenue of $95,723 million for the 16 weeks ended August 30, 2026.
*   **Filing:** 8-K Exhibit 99.1 (Accession 0000909832-26-000084)
*   **Period:** 16 Weeks Ended August 30, 2026
*   **Unit:** USD (millions)
*   **Filing Line:** "Total revenue"

**11. Quarter GAAP Diluted EPS**
Costco reported quarter GAAP diluted earnings per share of $6.75 for the 16 weeks ended August 30, 2026.
*   **Filing:** 8-K Exhibit 99.1 (Accession 0000909832-26-000084)
*   **Period:** 16 Weeks Ended August 30, 2026
*   **Unit:** USD/share
*   **Filing Line:** "Net income for the fourth quarter was $2.998 billion, $6.75 per diluted share"

**12. Quarter Revenue Growth**
Quarter revenue growth was 11.10%.
*   **Formula:** (95,723 - 86,156) / 86,156
*   **Inputs:** Current quarter revenue $95,723 million; Prior year same quarter revenue $86,156 million.
*   **Source:** Code-supplied calculation.

**13. FY-EPS P/E**
The FY-EPS P/E ratio is 47.79.
*   **Formula:** 992.13 / 20.76
*   **Inputs:** Share price $992.13 (dated 2026-10-27, source: Nasdaq API); Latest fiscal-year diluted EPS $20.76.
*   **Label:** FY-EPS P/E (not TTM P/E).
*   **Source:** Code-supplied calculation.

**Peer Operating Margins**
*   **Walmart Inc. (WMT):** Operating margin of 4.18% for fiscal year ended January 31, 2026.
    *   **Formula:** 29,825,000,000 / 713,163,000,000
    *   **Denominator:** "Total revenues" (WMT 10-K, Accession 0000104169-26-000055).
*   **Target Corp (TGT):** Operating margin of 4.88% for fiscal year ended January 31, 2026.
    *   **Formula:** 5,117,000,000 / 104,780,000,000
    *   **Denominator:** "Net sales" (TGT 10-K, Accession 0000027419-26-000016).
*   **BJ's Wholesale Club Holdings, Inc. (BJ):** Operating margin of 3.81% for fiscal year ended January 31, 2026.
    *   **Formula:** 816,604,000 / 21,457,274,000
    *   **Denominator:** "Total revenues" (BJ 10-K, Accession 0001531152-26-000007).

**Annual XBRL source details**

- Total revenue: $303,154 million at 2026-08-30; prior $275,235 million at 2025-08-31; XBRL tag `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`; 10-K accession 0000909832-26-000093; source: https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/0000909832-26-000093-index.html.
- Operating income: $11,685 million at 2026-08-30; prior $10,383 million at 2025-08-31; XBRL tag `us-gaap:OperatingIncomeLoss`; 10-K accession 0000909832-26-000093; source: https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/0000909832-26-000093-index.html.
- Net income: $9,226 million at 2026-08-30; prior $8,099 million at 2025-08-31; XBRL tag `us-gaap:NetIncomeLoss`; 10-K accession 0000909832-26-000093; source: https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/0000909832-26-000093-index.html.
- Diluted earnings per share: $20.76 at 2026-08-30; prior $18.21 at 2025-08-31; XBRL tag `us-gaap:EarningsPerShareDiluted`; 10-K accession 0000909832-26-000093; source: https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/0000909832-26-000093-index.html.
- Stockholders' equity: $35,803 million at 2026-08-30; prior $29,164 million at 2025-08-31; XBRL tag `us-gaap:StockholdersEquity`; 10-K accession 0000909832-26-000093; source: https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/0000909832-26-000093-index.html.
- Long-term debt: $3,914 million at 2026-08-30; prior $5,713 million at 2025-08-31; XBRL tag `us-gaap:LongTermDebtNoncurrent`; 10-K accession 0000909832-26-000093; source: https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/0000909832-26-000093-index.html.
- Current portion of long-term debt: $2,248 million at 2026-08-30; prior $75 million at 2025-08-31; XBRL tag `us-gaap:LongTermDebtCurrent`; 10-K accession 0000909832-26-000093; source: https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/0000909832-26-000093-index.html.
- Net cash provided by operating activities: $15,817 million at 2026-08-30; prior $13,335 million at 2025-08-31; XBRL tag `us-gaap:NetCashProvidedByUsedInOperatingActivities`; 10-K accession 0000909832-26-000093; source: https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/0000909832-26-000093-index.html.
- Additions to property and equipment: $6,435 million at 2026-08-30; prior $5,498 million at 2025-08-31; XBRL tag `us-gaap:PaymentsToAcquirePropertyPlantAndEquipment`; 10-K accession 0000909832-26-000093; source: https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/0000909832-26-000093-index.html.

**Price and peer source details**

- FY-EPS P/E: 47.7905x = 992.13 / 20.76. Price date: 2026-10-27; price source: https://api.nasdaq.com/api/quote/COST/historical?assetclass=stocks&fromdate=2026-10-27&todate=2026-10-31&limit=100. EPS period end: 2026-08-30; EPS tag: `us-gaap:EarningsPerShareDiluted`; 10-K accession 0000909832-26-000093. Not TTM P/E.
- Walmart Inc. (WMT) operating margin: 4.1821% = 29,825 / 713,163 million; period end 2026-01-31; denominator line label `Total revenues`; revenue tag `us-gaap:Revenues`; operating-income tag `us-gaap:OperatingIncomeLoss`; 10-K accession 0000104169-26-000055.
- TARGET CORP (TGT) operating margin: 4.8836% = 5,117 / 104,780 million; period end 2026-01-31; denominator line label `Net sales`; revenue tag `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`; operating-income tag `us-gaap:OperatingIncomeLoss`; 10-K accession 0000027419-26-000016.
- BJ's Wholesale Club Holdings, Inc. (BJ) operating margin: 3.8057% = 817 / 21,457 million; period end 2026-01-31; denominator line label `Total revenues`; revenue tag `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`; operating-income tag `us-gaap:OperatingIncomeLoss`; 10-K accession 0001531152-26-000007.

# Future Developments and Strategic Recommendations

The company continues to expand its warehouse base. "We opened 28 new warehouses, including three relocations, for a total of 25 net new warehouses: 18 in the U.S., five in our Canadian segment, and two in our Other International segment, compared to 27 new warehouses, including three relocations, in 2025." (10-k.txt:1030).

Executive membership penetration is a growth lever. "Executive members represented 42,300, 38,700, and 35,400 of total paid members in 2026, 2025, and 2024." (10-k.txt:769). Executive members represented approximately 75.2% of worldwide net sales in 2026. (10-k.txt:769).

Tariffs impact merchandise costs. "Government actions in various countries relating to tariffs affect the costs of some of our merchandise." (10-k.txt:1015). The fourth quarter 2026 results included a non-recurring benefit of $0.15 per diluted share from IEEPA tariff refunds. (exhibit-99-1.txt:20).

The filing does not establish a claim regarding specific future warehouse opening targets beyond the 2026 results. The filing does not establish a claim regarding specific future pricing actions beyond the stated philosophy of maintaining competitive values.

# Investment Recommendation

**Recommendation: Hold**

**Thesis**
Costco shows strong operational execution. The company reported 10% net sales growth and 14% net income growth for fiscal year 2026. The worldwide membership renewal rate was 89.8%. However, the supplied analysis lacks a valuation benchmark to establish intrinsic value.

**Deciding Number**
The FY-EPS P/E ratio is 47.79. This figure uses a share price of $992.13 dated 2026-10-27 and FY2026 diluted EPS of $20.76.

**Limitation**
One multiple without a suitable comparison cannot establish intrinsic value. The supplied peer data includes operating margins for Walmart, Target, and BJ's Wholesale Club. It does not include peer P/E ratios. Therefore, the 47.79 P/E ratio cannot be assessed for relative value. High growth and customer retention alone do not make the stock attractive without a valuation anchor.

This recommendation is not financial advice.

---

This is a learning exercise, not financial advice.

AI assistance: OpenAI Codex and Purdue GenAI Studio. I verified the sources myself; the judgments are mine.

Any remaining errors are my own.
