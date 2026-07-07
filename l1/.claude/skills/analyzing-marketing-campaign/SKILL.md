---
name: analyzing-marketing-campaign
description: Analyze funnel and efficiency performance of weekly campaign data. Compare campaign performance across different platforms.
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
1. Table summarizing CTR  , CVR and compare them to these historical benchmarks for each channel
2. Table summarizing ROAS  , CPA , Net profit andcompare them to the targets: Target ROAS: 4.0x minimum Max CPA: $50 Net profit should be positive for each channel