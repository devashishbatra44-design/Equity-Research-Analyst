# Human Spinoff Screen Factors

Status: frozen by Devashish Batra before the first pre-registered run

Do not ask AI to select, weight, or revise these factors before the first pre-registered run.

## Screen window

- Distribution start date: November 19, 2025
- Distribution end date or age limit: November 19, 2026, inclusive; full trailing-year window
- Index date: November 19, 2026
- Post-distribution window length: 365 calendar days. This line records the operational length implied by the approved full trailing-year choice. It does not amend F1, F2, F3, their weights, or their missing-data rules.
- Human decision: Devashish Batra selected the full trailing-year window on November 19, 2026.

## Factors

| Factor ID | Filing fact or code-built fact | Direction | Weight | Missing-data rule | Reason written by Devashish |
|---|---|---|---:|---|---|
| F1 | Child market capitalization is 10% or less of the parent's market capitalization at the first regular close after distribution. | lower | 1 | unranked | A relatively small child may face mandate-based selling and receive less investor attention. |
| F2 | The child made no debt-funded cash payment to the parent as part of the separation. | no | 1 | unranked | This rule avoids a child that starts with debt incurred to fund a payment to the parent. |
| F3 | An officer or director reported at least one open-market Form 4 transaction-code `P` purchase after distribution and no later than 90 calendar days after distribution or the index date, whichever occurs first. | yes | 1 | unranked | An open-market insider purchase uses the insider's own capital and may indicate alignment with outside shareholders. |

Allowed directions are `higher`, `lower`, `yes`, or `no` after the code contract is fixed. A weight of 0 must change only that factor's contribution.

## Freeze record

- Frozen by: Devashish Batra
- Frozen at, Eastern: November 19, 2026 at 9:09:27 AM EST
- Approval statement: "I, Devashish Batra, select and approve factors F1, F2, and F3 exactly as writtrn, with equal weights of 1 and the unranked missing-data rule."
- Commit or file hash: Pending the first authorized commit. The local freeze precedes the first pre-registered run.
- Change rule after freeze: Do not alter these factors for the first pre-registered run. Any later change requires a dated amendment from Devashish Batra. Preserve the original factors and do not use an amendment to rerank an earlier run.
