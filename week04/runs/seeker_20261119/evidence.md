# Seeker Validation Evidence

Run date: November 19, 2026

Purpose: Apply the frozen factors to the two human-approved controls before a broader registry run. This is not a complete census of every Form 10 registrant in the trailing-year window.

## Frozen configuration

- Distribution window: November 19, 2025 through November 19, 2026, inclusive.
- Index date: November 19, 2026.
- F1: Child market capitalization is 10% or less of parent market capitalization at the first regular close after distribution.
- F2: The child made no debt-funded cash payment to the parent as part of the separation.
- F3: An officer or director reported an open-market Form 4 transaction-code `P` purchase after distribution and by the earlier of 90 calendar days after distribution or the index date.
- Each factor has a weight of 1. Each missing-data rule is `unranked`.

## FedEx Freight registry facts

- Child: FedEx Freight Holding Company, Inc. (FDXF), CIK 0002082247.
- Parent: FedEx Corporation (FDX), CIK 0001048911.
- Form 10-12B: accession 0001104659-26-004329, filed January 16, 2026.
- Final Information Statement: Exhibit 99.1 to accession 0001104659-26-060223, dated May 13, 2026.
- Distribution ratio: 1 FDXF share for every 2 FDX shares held at the record date.
- Record date: May 15, 2026, close of business.
- Distribution date: June 1, 2026 at 12:01 a.m. Central Time.
- Parent completion Form 8-K: accession 0001104659-26-068519, accepted June 1, 2026 at 6:42:52 a.m. Eastern Time.
- Filing sections: Final Information Statement, `Questions and Answers About the Spin-Off`, `The Spin-Off`, and `Capitalization`; parent Form 8-K, Items 1.01, 2.01, 8.01, and 9.01.

Official SEC sources:

- <https://www.sec.gov/Archives/edgar/data/2082247/000110465926004329/0001104659-26-004329-index.htm>
- <https://www.sec.gov/Archives/edgar/data/2082247/000110465926060223/tm2520565d14_ex99-1.htm>
- <https://www.sec.gov/Archives/edgar/data/1048911/000110465926068519/0001104659-26-068519-index.htm>

## Factor evidence

### F1 — false; 0 points

The official June 1, 2026 regular closes were $149.53 USD for FDXF and $338.49 USD for FDX. The FedEx Freight final information statement states that FedEx distributed 80.1% of FDXF and that each eligible FDX share received 0.50 FDXF share.

The market-cap ratio does not require a separate parent share count because the same parent share count appears in both sides of the derivation:

`FDXF market cap / FDX market cap = (0.50 / 0.801) × ($149.53 / $338.49) = 0.2757528303`, or 27.575%.

The frozen F1 threshold is 10% or less. A 27.575% ratio makes F1 false.

Capital IQ's transaction export reports a June 1, 2026 `Spin-Off Security Share Price` of $160.37 USD. That transaction-page value does not equal the official Nasdaq regular close of $149.53 USD. The frozen rule requires the first regular close, so the run does not use $160.37.

Sources and periods:

- FDXF: $149.53 USD regular close on June 1, 2026. Nasdaq official historical endpoint, <https://api.nasdaq.com/api/quote/FDXF/historical?assetclass=stocks&fromdate=2026-01-01&todate=2026-11-19&limit=5000>.
- FDX: $338.49 USD regular close on June 1, 2026. Nasdaq official historical endpoint, <https://api.nasdaq.com/api/quote/FDX/historical?assetclass=stocks&fromdate=2026-01-01&todate=2026-11-19&limit=5000>.
- Distribution terms: FedEx Freight Final Information Statement dated May 13, 2026, `Questions and Answers About the Spin-Off` and `The Spin-Off`, accession 0001104659-26-060223.
- Capital IQ cross-check: `FedEx Freight Holding Company Inc NYSE FDXF Transaction Details Spin Off Split Off.rtf`, exported November 19, 2026. The licensed raw export remains outside Git.

### F2 — false; 0 points

FedEx Freight stated that it incurred approximately $4.3 billion of indebtedness in contemplation of the spin-off. It expected to distribute approximately $4.1 billion of the net borrowing proceeds to FedEx at the spin-off closing. The amounts are in U.S. dollars and are stated in the May 13, 2026 final information statement.

The frozen F2 rule requires no debt-funded cash payment to the parent. The approximately $4.1 billion payment makes F2 false.

Source: FedEx Freight Final Information Statement dated May 13, 2026, `Capitalization`, note (b), and `Description of Certain Indebtedness — Senior Notes`, accession 0001104659-26-060223.

### F3 — false; 0 points

The eligible transaction window began after June 1, 2026 and ended August 30, 2026, which is 90 calendar days after distribution.

The SEC submissions record contained 34 Forms 4 or 4/A filed from June 1 through August 30, 2026. The transaction tables contained codes `A` and `J`. No transaction table contained code `P`. The same-day June 1 transactions were not eligible under the frozen rule in any case.

The search included officers and directors. A complete search with no qualifying purchase is `false`, not missing.

Official SEC source: <https://data.sec.gov/submissions/CIK0002082247.json>.

Form 4 accession numbers reviewed:

- 0001104659-26-068887
- 0001628280-26-040366, 0001628280-26-040369, 0001628280-26-040374, 0001628280-26-040376, 0001628280-26-040382, 0001628280-26-040384, 0001628280-26-040386, 0001628280-26-040387, 0001628280-26-040388, 0001628280-26-040389, and 0001628280-26-040395
- 0001628280-26-046552, 0001628280-26-046553, 0001628280-26-046554, 0001628280-26-046555, 0001628280-26-046556, 0001628280-26-046557, 0001628280-26-046558, 0001628280-26-046559, 0001628280-26-046560, 0001628280-26-046562, 0001628280-26-046565, 0001628280-26-046567, 0001628280-26-046570, 0001628280-26-046571, 0001628280-26-046572, and 0001628280-26-046573
- 0001628280-26-048491
- 0001628280-26-053499, 0001628280-26-053503, 0001628280-26-053509, and 0001628280-26-053516
- 0001628280-26-055715

## PIMCO control

- Registrant: PIMCO Asset-Based Lending Company LLC, CIK 0002073537.
- Form 10-12G: accession 0001193125-25-161296, filed July 21, 2025.
- Filing result: dropped as a non-spinoff.
- Reason: The registrant directly registered its existing interests in anticipation of future Exchange Act Section 12(g) registration requirements. The filing does not describe a parent distributing child shares.
- Filing sections: `Explanatory Note`; Item 1, `Business Overview` and `Reporting Obligations`.
- Official SEC source: <https://www.sec.gov/Archives/edgar/data/2073537/000119312525161296/0001193125-25-161296-index.htm>.

## Result

FedEx Freight is ranked with 0 of 3 points because F1, F2, and F3 are false. PIMCO is dropped for its filing-proven non-spinoff reason.

This validation does not make an investment recommendation.
