# Tax Accounting Method

## Overview

This system uses **Average Cost Basis** method for calculating profit/loss on all sales, including partial sales.

## How It Works

### For Long Positions

When you sell shares (partial or full), profit/loss is calculated as:

```
Profit = Sale Proceeds - Cost Basis of Shares Sold
```

Where:
- **Sale Proceeds** = Quantity Sold × Sale Price
- **Cost Basis of Shares Sold** = Quantity Sold × Average Cost Per Share (before the sale)

### Example

You buy:
- 1 share at $20
- 1 share at $30  
- 1 share at $40

**Average Cost** = ($20 + $30 + $40) / 3 = **$30.00**

When you sell 1 share at $45:
- **Sale Proceeds** = 1 × $45 = $45.00
- **Cost Basis** = 1 × $30.00 = $30.00
- **Profit** = $45.00 - $30.00 = **$15.00**

After the sale:
- Remaining position: 2 shares
- Remaining cost basis: $60.00 (2 × $30.00)
- Average cost remains: $30.00

### For Short Positions

When you cover shares (partial or full), profit/loss is calculated as:

```
Profit = Proceeds from Short Sale - Cost to Cover
```

Where:
- **Proceeds from Short Sale** = Quantity Covered × Average Proceeds Per Share (from when short was opened)
- **Cost to Cover** = Quantity Covered × Cover Price

## Tax Reporting

### When Profit is Calculated

Profit/loss is now calculated and reported for:
- ✅ **Partial sales** of long positions
- ✅ **Full sales** of long positions
- ✅ **Partial covers** of short positions
- ✅ **Full covers** of short positions

### Accumulated Gains

The report shows **Accumulated Gains** which is the running total of all realized profits/losses. This is updated every time shares are sold (not just when positions are closed).

## Comparison with Other Methods

### FIFO (First In, First Out)
- **Default method** for US tax purposes if not specified
- Requires tracking individual lots
- More complex to implement
- **Not used in this system**

### Average Cost Basis
- **Used in this system**
- Simpler to calculate and track
- Acceptable for tax purposes
- Matches the position tracking method already in use

### Specific Identification
- Allows choosing which specific shares to sell
- Requires lot tracking with purchase dates
- **Not used in this system**

## Important Notes

1. **Partial Sales**: Every partial sale now calculates and reports profit/loss immediately, which is correct for tax purposes.

2. **Average Cost**: The average cost per share is recalculated after each purchase, but remains constant during sales (you're selling at the average cost).

3. **Tax Compliance**: This method is acceptable for tax reporting purposes, though FIFO is the default if you don't specify a method to the IRS.

4. **Consistency**: The same average cost basis method is used for both position tracking and profit calculation, ensuring consistency.


