---
name: analyzing-marketing-campaign
# description: nalyze funnel and efficiency performance of weekly campaign data. Compare campaign performance across different platforms.
description: Analyze weekly marketing campaign performance data across channels. Use when analyzing multi-channel digital marketing data to calculate funnel metrics (CTR, CVR) and compare to benchmarks, compute cost and revenue efficiency metrics (ROAS, CPA, Net Profit), or get budget reallocation recommendations based on performance rules.
---

### Input Data format
CSV file format.
Columns 
1. date 
2. campaign_Name
3. channel
4. segment
5. impressions
6. clicks
7. conversions
8. spend
9. revenue
10.  orders



### Benchmark
Channel, CTR, CVR 
Facebook_Ads, 2.5%, 3.8%
Google_Ads, 5.0%, 4.5%
TikTok_Ads, 2.0%, 0.9%
Email, 15.0%, 2.1%


### Budget reallocation
If budget reallocation proposal is requested please refer to ./references/budget_reallocation_rules.md for the reallocation rules to make suggestion . Pleaes conclude how much can be improved with the budget reallocation

### Python script
script/analyze_campaign.py has 3 functions
1. data quality check
2. CTR and CVR analysis by channel  
    *  CTR (Click Through Rate)=  Clicks/Impressions
    *  CVR (Conversion Rate) = Conversions/Clicks
3. efficency performance analysis 
    * ROAS (Return on Ad Spend) = Revenue/Spend
    * CPA (Cost Per Acquisition) = Spend / Conversions
    * Net profit = Revenue - Total Costs:
      
        Total Costs = Spend + (Orders × Shipping Cost) + (Revenue × Product Cost Percentage)

        Assume Shipping Cost is 8 dollars on average per order, and Product Cost Percentage is 35%
    
    
And compare them to the targets: Target ROAS: 4.0x minimum Max CPA: $50 Net profit should be positive    

usage: python analyze_campaign.py inputdata.csv


### output 
1. Table summarizing CTR  , CVR and compare them to these historical benchmarks for each channel , please list benchmark value  , CTR , CVR and delta in your output
2. Table summarizing ROAS  , CPA , Net profit andcompare them to the targets: Target ROAS: 4.0x minimum Max CPA: $50 Net profit should be positive for each channel


### Excel Report Generation

When asked to produce an Excel report, use the `scripts/create_report.py` script in the skill directory. This generates a 4-sheet `.xlsx` file with color-coded results.

**Prerequisites:**
- Project virtual environment at `.venv` with `openpyxl>=3.1.0` installed (`requirements.txt`)
- Python 3.13

**Usage:**
```bash
# Default: campaign_data_week1.csv → campaign_report_week1.xlsx
.venv/bin/python .claude/skills/analyzing-marketing-campaign/scripts/create_report.py

# Custom input/output
.venv/bin/python .claude/skills/analyzing-marketing-campaign/scripts/create_report.py <input.csv> <output.xlsx>
```

**Sheets produced:**

| Sheet | Contents |
|---|---|
| **Executive Summary** | Key findings, channel performance table (Revenue, Spend, ROAS, CPA, Net Profit, Margin), budget reallocation classification and new budget tables |
| **Funnel Analysis** | CTR and CVR by channel with benchmark comparisons and deltas, per-campaign breakdown with color coding (green = above benchmark, red = below) |
| **Efficiency Analysis** | ROAS, CPA, and Net Profit by channel and campaign, profit bridge showing where money goes (Revenue − Spend − Shipping − Product Cost = Net Profit) |
| **Raw Data** | All rows from the source CSV with proper number formatting |

**Design standards** (from `document-skills:xlsx` skill):
- Arial font throughout
- Blue header rows with white text
- Green fill = above target/benchmark or positive profit
- Red fill = below target/benchmark or negative profit
- Yellow fill = maintain/neutral
- Excel formulas (SUMIF, division) used where possible so the report recalculates when raw data changes
- Recalculation via LibreOffice: `python /path/to/xlsx/scripts/recalc.py output.xlsx` (optional, formulas auto-calculate when opened in Excel/Google Sheets)