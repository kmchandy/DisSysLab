# Office: aapl_tsla_price_mailer

## Purpose
Fetch the latest AAPL and TSLA closing prices from Yahoo Finance and email a one-sentence summary to kmchandy@gmail.com. Runs once immediately.

## Trigger
- manual / immediate (run once)

## Roles
- fetcher
- mailer

## Workflow
1. fetcher fetches the most recent closing price for AAPL from Yahoo Finance
2. fetcher fetches the most recent closing price for TSLA from Yahoo Finance
3. fetcher passes both prices to mailer
4. mailer composes a one-sentence summary in the form: "AAPL closed at $X and TSLA closed at $Y."
5. mailer sends the summary email to kmchandy@gmail.com
