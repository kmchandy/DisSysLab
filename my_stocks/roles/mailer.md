# Role: mailer

## Purpose
Compose a one-sentence summary of AAPL and TSLA closing prices and send it to kmchandy@gmail.com.

## Inputs
- aapl_closing_price: number (USD)
- aapl_price_date: date
- tsla_closing_price: number (USD)
- tsla_price_date: date

## Outputs
- confirmation that the email was sent

## Steps
1. Compose the subject line: "AAPL & TSLA Closing Prices – <date>"
2. Compose the body as a single sentence: "AAPL closed at $<aapl_closing_price> and TSLA closed at $<tsla_closing_price> on <date>."
3. Send the email to kmchandy@gmail.com using the configured email service (e.g. SMTP or SendGrid)

## Error handling
- If sending fails, raise an error with the SMTP/API error message
