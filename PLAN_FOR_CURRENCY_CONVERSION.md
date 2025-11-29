# Plan for Currency Conversion (USD to GBP)

## Overview

This document outlines the plan for implementing currency conversion from USD to GBP for UK tax reporting purposes. All trading activities are currently in USD, but UK tax returns require reporting in GBP.

## HMRC Requirements

### Official Guidance

According to HMRC guidance for foreign chargeable gains:
- **Sale proceeds** (consideration received) should be converted to GBP using the exchange rate **on the date of disposal**
- **Cost basis** (allowable deductions) should be converted to GBP using the exchange rate **on the date the expenditure was incurred** (purchase date)
- **Profit/Loss** is then calculated in GBP: `GBP Sale Proceeds - GBP Cost Basis`

### Key Principles

HMRC does **not** mandate a specific exchange rate source, but requires:
1. **Consistency**: Use the same method/source for all transactions
2. **Reliability**: Use a reputable source
3. **Documentation**: Record the source and methodology used

## Recommended Approach

### Pre-processing Strategy

**Enrich `taxable_activities.json` with currency conversion data:**

For each event in the file, add two fields:
1. `exchange_rate_usd_gbp`: The USD/GBP exchange rate on the transaction date
2. `price_gbp`: The price converted to GBP (calculated as `price * exchange_rate_usd_gbp`)

**Why this approach:**
- Separation of concerns: Currency conversion happens once during pre-processing
- Explicit data: Exchange rates are visible in the data for audit purposes
- Minimal code changes: Existing calculation logic can use `price_gbp` instead of `price`
- Performance: Exchange rates fetched once, not repeatedly during calculations
- Flexibility: Can recalculate GBP amounts if needed

### Implementation Steps

1. **Pre-processing script**: Create a script that:
   - Reads `taxable_activities.json`
   - Extracts unique transaction dates
   - Fetches exchange rates for each date from API
   - Adds `exchange_rate_usd_gbp` and `price_gbp` to each event
   - Saves enriched data (to new file or overwrites)

2. **Update existing code**: Modify `balance_tracker.py` and `fiscal_year_report.py` to:
   - Use `price_gbp` when available (or calculate from `price * exchange_rate_usd_gbp`)
   - Calculate all P/L in GBP using GBP amounts

## Exchange Rate Sources

### Acceptable Sources

HMRC accepts exchange rates from various reputable sources. The key is consistency and reliability.

### Options Considered

1. **APILayer** (Paid subscription)
   - ✅ Reputable commercial provider
   - ✅ Provides historical daily spot rates
   - ✅ Acceptable to HMRC if used consistently
   - ❌ Requires paid subscription

2. **exchangerate-api.com** (Free tier available)
   - ✅ Free tier available (1,500 requests/month)
   - ✅ Provides historical daily spot rates
   - ✅ Acceptable to HMRC if used consistently
   - ⚠️ Free tier has rate limits

3. **Bank of England**
   - ✅ Official UK source
   - ❌ Provides monthly averages, not daily spot rates
   - ⚠️ Not ideal for daily transaction dates

4. **HMRC Published Rates**
   - ✅ Official source
   - ❌ Monthly averages, not daily spot rates
   - ⚠️ Not ideal for daily transaction dates

### Recommendation

For capital gains tax reporting, **daily spot rates** are needed on transaction dates. Either:
- Continue using **APILayer** if already subscribed (acceptable and reliable)
- Use **exchangerate-api.com free tier** if volume fits within limits

## Technical Considerations

### Rate Fetching Strategy

- **Batch unique dates**: Extract all unique transaction dates first, then fetch rates in batch to minimize API calls
- **Caching**: Cache exchange rates to avoid refetching (store in JSON file)
- **Error handling**: Handle cases where rates cannot be fetched (missing dates, API failures)
- **Data format**: Ensure JSON structure supports new fields

### Cost Basis Calculation in GBP

When calculating cost basis in GBP:
- For **purchases**: Use exchange rate on purchase date
- For **average cost basis**: Each purchase contributes to average using its purchase-date exchange rate
- For **sales**: Use exchange rate on sale date for proceeds

Example:
- Buy 10 shares at $100 on Jan 1 (rate: 0.75) → Cost basis: £750
- Buy 10 shares at $120 on Feb 1 (rate: 0.76) → Cost basis: £912
- Average cost: £83.1 per share
- Sell 5 shares at $150 on Mar 1 (rate: 0.77) → Proceeds: £577.50
- Profit: £577.50 - (5 × £83.1) = £161.50

## Next Steps

1. ✅ Document plan (this file)
2. ⏳ Create pre-processing script to enrich `taxable_activities.json`
3. ⏳ Update `balance_tracker.py` to use GBP values
4. ⏳ Update `fiscal_year_report.py` to use GBP values
5. ⏳ Update `TAX_ACCOUNTING.md` with currency conversion documentation
6. ⏳ Test with sample data
7. ⏳ Update reports to show GBP values

## Notes

- This approach maintains backward compatibility (USD values still present)
- Exchange rates are stored with each transaction for audit trail
- Can switch exchange rate sources if needed (just re-run pre-processing)

