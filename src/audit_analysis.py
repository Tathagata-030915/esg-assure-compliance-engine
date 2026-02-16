import pandas as pd
import numpy as np
import os

# 1. Load the data
data_path = '../data/suppliers_raw.csv'
if not os.path.exists(data_path):
    print("❌ Error: suppliers_raw.csv not found in data folder!")
    exit()

df = pd.read_csv(data_path)

# 2. Define Audit Rules
exceptions = []

print("🔍 Starting Audit Analysis...")

# --- Rule 1: Carbon Emission Outliers (Z-Score > 3) ---
for industry in df['Industry'].unique():
    industry_subset = df[df['Industry'] == industry]
    mean = industry_subset['Carbon_Emissions_MT'].mean()
    std = industry_subset['Carbon_Emissions_MT'].std()
    
    # Identify outliers in this industry
    outliers = industry_subset[industry_subset['Carbon_Emissions_MT'] > (mean + 3 * std)]
    for idx, row in outliers.iterrows():
        exceptions.append({
            'Supplier_ID': row['Supplier_ID'],
            'Issue': 'Carbon Outlier',
            'Details': f"Emissions ({row['Carbon_Emissions_MT']}) far exceed industry avg ({round(mean, 2)})",
            'Risk_Level': 'High'
        })

# --- Rule 2: Diversity Reporting Gaps ---
missing_diversity = df[df['Social_Diversity_Score_%'].isna()]
for idx, row in missing_diversity.iterrows():
    exceptions.append({
        'Supplier_ID': row['Supplier_ID'],
        'Issue': 'Reporting Gap',
        'Details': 'Diversity score missing or null.',
        'Risk_Level': 'Medium'
    })

# --- Rule 3: Sustainability Paradox (Zero Water in Mfg) ---
mfg_zero_water = df[(df['Industry'] == 'Manufacturing') & (df['Water_Usage_m3'] == 0)]
for idx, row in mfg_zero_water.iterrows():
    exceptions.append({
        'Supplier_ID': row['Supplier_ID'],
        'Issue': 'Logical Anomaly',
        'Details': 'Manufacturing reported 0 water usage (Potential Greenwashing).',
        'Risk_Level': 'High'
    })

# 3. Create Exception Report
exceptions_df = pd.DataFrame(exceptions)
exceptions_df.to_csv('../data/audit_exceptions.csv', index=False)

print(f"✅ Audit Complete. Found {len(exceptions_df)} exceptions.")
print("📄 Report saved to '../data/audit_exceptions.csv'")