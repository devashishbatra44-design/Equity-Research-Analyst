# Equity Research Desk Data Pipeline

Build the data layer of an equity research desk in Python. Model the workflow on Section 3.1 of Francis and Zhang (2026). Do not implement the model or agent roles yet.

Create production-quality code that works for different U.S. public companies. Do not hard-code any company name, ticker, CIK, filing, peer, date, price, fiscal year, or financial value.

## SEC configuration

1. Read the SEC User-Agent from `SEC_USER_AGENT` in the `.env` file in the current folder.
2. Send `SEC_USER_AGENT` in the `User-Agent` header of every SEC request.
3. Do not print, log, save, or expose the value of `SEC_USER_AGENT`.
4. Stop with a clear error if `SEC_USER_AGENT` is missing or empty.
5. Limit SEC requests to no more than five requests per second.
6. Use a 30-second request timeout.
7. Retry HTTP 429 and 5xx responses up to three times.
8. Use exponential backoff between retries.
9. Stop with a clear explanation after an HTTP 403 response.
10. Identify every request with the required SEC User-Agent.

## Command-line interface

The program must accept:

- A required ticker argument.
- An optional `--peers` argument with a comma-separated list of tickers.
- An optional `--price` argument with a numeric share price.
- An optional `--step` argument with an integer from 1 through 7.

Normalize ticker symbols to uppercase.

Reject an empty ticker, invalid `--step` value, nonnumeric `--price` value, or price that is not greater than zero.

## Execution rules

1. During a complete run, print and run Steps 1 through 7 in order.
2. Print the step number and name when each step starts.
3. If `--step N` is supplied, run only Step N.
4. For a single-step run, load required inputs from the newest successful run folder for the same ticker.
5. Stop with a clear error if a single step requires saved inputs that are unavailable.
6. Do not silently run an earlier step during a single-step run.
7. Mark a step as successful only after it creates and validates its required output.
8. Record each step's status in the run manifest.

## Output folder

For a complete run, create this folder after resolving the company:

`company_ticker_YYYYMMDD_HHMMSS`

Use the legal company name returned by the SEC. Replace characters that are unsafe in a folder name.

Use the local run time in the folder name. Save the time zone and a UTC timestamp in the manifest.

Create these files when applicable:

```text
company_ticker_YYYYMMDD_HHMMSS/
    manifest.json
    filings.json
    10-k.txt
    10-q.txt
    8-k.txt
    exhibit-99-1.txt
    facts.json
    facts.csv
    calculations.json
    peers.json
    peers.csv
```

Use UTF-8 for text files.

## Step 1: Resolve the ticker

1. Download SEC `company_tickers.json`.
2. Match the input ticker without regard to letter case.
3. Resolve the ticker to its SEC CIK and legal company name.
4. Preserve the numeric CIK.
5. Also create the zero-padded 10-digit CIK required by SEC data endpoints.
6. Print the ticker, legal company name, and CIK.
7. Stop clearly if the ticker is absent or ambiguous.
8. Save the result in the manifest.

## Step 2: Select the filings

1. Retrieve the company's filing history from the EDGAR submissions API.
2. Read both the recent-filings section and any referenced historical submission files.
3. Find the latest filing whose form is exactly `10-K`.
4. Find the latest filing whose form is exactly `10-Q`.
5. Find the latest filing whose form is exactly `8-K` and whose SEC submissions record contains Item 2.02.
6. Treat that 8-K as the earnings-release filing.
7. Exclude `10-K/A`, `10-Q/A`, and `8-K/A`.
8. Select the latest qualifying filing by accepted timestamp.
9. Open the EDGAR filing index page for each selected filing.
10. Read and verify the “Accepted” date and time shown on that index page.
11. Print these fields for each filing:

    - Form.
    - Filing date.
    - Reporting-period end.
    - Accession number.
    - Primary document.
    - Accepted date and time.
    - EDGAR index URL.

12. Stop with a clear error if a required filing is unavailable.
13. Do not silently substitute another form.
14. Save the filing metadata and source URLs in `filings.json` and `manifest.json`.

## Step 3: Download and convert the documents

1. Download the selected 10-K primary document.
2. Download the selected 10-Q primary document.
3. Download the selected 8-K primary document.
4. Read the selected 8-K filing index.
5. Find an exhibit whose SEC document type is `EX-99.1`.
6. Prefer an `EX-99.1` whose description or filename contains `earnings`, `results`, `release`, or `press`.
7. Treat the selected `EX-99.1` as the earnings release.
8. If several exhibits remain equally valid, print all candidates and stop with an ambiguity error.
9. Convert the 10-K, 10-Q, 8-K, and Exhibit 99.1 to plain text.
10. Remove scripts, styles, navigation content, and repeated HTML formatting.
11. Preserve headings, paragraphs, table text, and meaningful line breaks when possible.
12. Do not summarize or rewrite the source text.
13. Save the four text files in the run folder.
14. Record each source URL, local filename, accession number, and retrieval status in the manifest.
15. Stop clearly if a downloaded document is empty or cannot be converted to usable text.

## Step 4: Retrieve annual XBRL company facts

Retrieve the company's XBRL company facts from the SEC.

Collect these concepts:

1. Total revenue.
2. Operating income.
3. Net income.
4. Diluted earnings per share.
5. Stockholders' equity.
6. Long-term debt.
7. Current portion of long-term debt.
8. Net cash provided by operating activities.
9. Additions to property and equipment.

Maintain an ordered list of candidate US-GAAP tags for each concept. Keep the tag lists in one visible and maintainable section of the code.

### Fact classifications

Treat these as duration facts:

- Total revenue.
- Operating income.
- Net income.
- Diluted earnings per share.
- Net cash provided by operating activities.
- Additions to property and equipment.

Treat these as instant facts:

- Stockholders' equity.
- Long-term debt.
- Current portion of long-term debt.

### Units

1. Use USD for monetary facts.
2. Use USD per share for diluted EPS.
3. Do not combine different currencies or incompatible units.
4. Print and save the unit for every value.

### Reference fiscal year

1. Use total revenue to determine the reference fiscal year.
2. Select the latest valid annual revenue observation from a filing whose form is `10-K` and whose fiscal period is `FY`.
3. Use that revenue observation's fiscal-year start, fiscal-year end, and fiscal-year label as the reference period.
4. Use the immediately preceding annual revenue period as the prior period.
5. Read all other duration concepts for the same annual periods as revenue.
6. Read instant concepts at the current and prior fiscal-year ends.
7. Do not combine facts from different fiscal periods.

### Candidate-tag selection

For each concept:

1. Examine every configured candidate tag.
2. Remove observations with an incompatible unit.
3. Remove observations that are not associated with a `10-K`.
4. Remove observations that do not represent an annual period when the concept is a duration fact.
5. Prefer a tag that contains valid current-year and prior-year observations.
6. Select the tag whose latest valid annual period is newest.
7. If several tags remain tied, use the declared candidate-tag priority order.
8. For duplicate observations with the same tag and period, use the observation with the latest filing date.
9. Record the selected tag and the reason for its selection.
10. Record rejected candidate tags and rejection reasons in `facts.json`.
11. Do not replace an unavailable fact with zero.
12. Do not infer a value by combining unrelated tags unless the calculation is explicitly required.

For each selected fact, print and save:

- Concept name.
- Selected XBRL tag.
- Selection reason.
- Unit.
- Fiscal year.
- Period start, when applicable.
- Period end.
- Value.
- Filing form.
- Filing date.
- Accession number.
- SEC source URL.
- Prior-year value and the same source fields.

Save the complete results in `facts.json` and a tabular version in `facts.csv`.

## Step 5: Calculate financial measures

Implement all calculations in Python.

For each calculation, print and save:

- Measure name.
- Formula.
- Input names.
- Input values.
- Units.
- Fiscal periods.
- Arithmetic.
- Result.
- Validation status.

Calculate these measures:

1. Revenue growth

   `(Current-year revenue - Prior-year revenue) / Prior-year revenue`

2. Operating margin

   `Current-year operating income / Current-year revenue`

3. Return on average equity

   `Current-year net income / ((Current-year stockholders' equity + Prior-year stockholders' equity) / 2)`

4. Debt to equity

   `(Current-year long-term debt + Current portion of long-term debt) / Current-year stockholders' equity`

5. Free cash flow

   `Net cash provided by operating activities - Additions to property and equipment`

6. Price-to-earnings ratio

   `--price / Current-year diluted EPS`

### Calculation rules

1. Include the current portion of long-term debt in debt to equity.
2. Treat additions to property and equipment as a positive expenditure amount in the free-cash-flow calculation.
3. Preserve the original SEC-reported value separately.
4. Calculate P/E only when `--price` is supplied and diluted EPS is available.
5. Label P/E as “Price divided by latest fiscal-year diluted EPS.”
6. Do not label the result as TTM P/E.
7. If diluted EPS is negative, calculate the arithmetic result but label the P/E as not economically meaningful.
8. Do not calculate a measure if an input is missing.
9. Do not divide by zero.
10. Print a clear reason when a calculation is unavailable.
11. Save the results in `calculations.json`.

## Step 6: Extract quarterly revenue and diluted EPS from the earnings release

1. Search the Exhibit 99.1 plain text.
2. Identify the text that states the reported quarter's total revenue.
3. Identify the text that states the reported quarter's diluted EPS.
4. Print the exact source lines or the smallest complete text block that contains each value.
5. Preserve enough surrounding text to identify the period, value, and unit.
6. Print the source filename and line number or line range.
7. Label the output as quoted source text.
8. Do not calculate, infer, paraphrase, or fabricate a quoted value.
9. If several values could satisfy the request, print the candidates and explain the ambiguity.
10. If a value is unavailable, state that it was not found.
11. Save the extracted text and its source location in `facts.json`.

## Step 7: Process the peers

For each ticker supplied through `--peers`:

1. Normalize the ticker to uppercase.
2. Resolve the ticker to its CIK and legal company name.
3. Retrieve the same nine annual XBRL concepts defined in Step 4.
4. Apply the same units, candidate tags, selection rules, and validation rules.
5. Establish the peer's reference fiscal year from its own revenue data.
6. Preserve the peer's fiscal-year end.
7. Do not imply that all peers use the same fiscal calendar.
8. Calculate the peer's operating margin with the same formula used for the main company.
9. Print and save:

    - Peer ticker.
    - Legal company name.
    - CIK.
    - Concept.
    - Value.
    - Unit.
    - Fiscal year.
    - Period end.
    - Selected tag.
    - Filing form.
    - Filing date.
    - Accession number.
    - Operating margin.
    - Validation status.

10. Continue with the remaining peers if one peer fails.
11. Record the failed peer and exact failure reason.
12. Save detailed peer data in `peers.json`.
13. Save a tabular comparison in `peers.csv`.

## Manifest requirements

The `manifest.json` file must contain:

- Program version.
- Run status.
- Step statuses.
- Local run time.
- UTC run time.
- Time zone.
- Command-line arguments.
- Main ticker.
- Peer tickers.
- Company name.
- CIK.
- Source URLs.
- Filing forms.
- Filing dates.
- Reporting periods.
- Accession numbers.
- Accepted timestamps.
- Selected XBRL tags.
- Tag-selection reasons.
- Output filenames.
- Retrieval errors.
- Validation errors.
- Unavailable values.

Do not store `SEC_USER_AGENT` or any other secret in the manifest.

## Validation requirements

Before reporting success:

1. Confirm that every selected filing has an accession number and accepted timestamp.
2. Confirm that every saved document contains usable text.
3. Confirm that all current-year duration facts use the reference annual period.
4. Confirm that all current-year instant facts use the reference fiscal-year end.
5. Confirm that all prior-year facts use the prior reference period.
6. Confirm that every calculation uses compatible units and periods.
7. Confirm that each reported fact has a tag, unit, period, filing, and source reference.
8. Confirm that all required JSON files contain valid JSON.
9. Confirm that all required CSV files contain headers.
10. Mark unavailable data honestly.
11. Do not fabricate or silently repair a value.

## Completion requirements

Complete the implementation. Do not stop after writing a plan.

Run the program with:

- One main ticker.
- At least three peers.
- A supplied share price.

Confirm that:

1. Steps 1 through 7 print in order.
2. The program finishes without an unhandled exception.
3. The run folder is created.
4. Every applicable output file is present.
5. The facts include their tags, units, periods, filings, and source references.
6. The calculations show their formulas and arithmetic.
7. Peer operating margins use the same definition.
8. No secret value appears in the console or saved files.

When finished, provide:

1. The exact command to install every required package.
2. The exact command to run a complete analysis with a ticker, peers, and price.
3. The exact command to run one step with `--step`.
4. A short description of every created source-code file.
5. A short description of every output file.
6. The path of the completed run folder.
7. Any unavailable values, ambiguous filings, validation failures, or remaining limitations.

If the program fails, show the exact command and the exact error text. Diagnose the cause and correct the implementation before reporting completion.
