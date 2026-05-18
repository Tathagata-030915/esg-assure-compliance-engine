import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# 1. Configuration - Set seed for reproducibility (Crucial for Audits)
np.random.seed(42)
num_suppliers = 1000

# 2. Industry-Specific Baselines (Real-world logic)
industries = {
    'Manufacturing': {'carbon': (5000, 15000), 'water': (2000, 8000), 'diversity': (10, 25)},
    'IT Services': {'carbon': (100, 500), 'water': (50, 200), 'diversity': (35, 50)},
    'Energy': {'carbon': (40000, 100000), 'water': (5000, 20000), 'diversity': (5, 15)},
    'Consumer Goods': {'carbon': (1000, 5000), 'water': (1000, 4000), 'diversity': (20, 40)},
    'Healthcare': {'carbon': (500, 2000), 'water': (500, 1500), 'diversity': (30, 45)}
}

data = []

for i in range(num_suppliers):
    industry = random.choice(list(industries.keys()))
    
    # Standard Data Generation
    carbon = np.random.uniform(*industries[industry]['carbon'])
    water = np.random.uniform(*industries[industry]['water'])
    diversity = np.random.uniform(*industries[industry]['diversity'])
    safety_incidents = np.random.poisson(lam=1.2) # Average 1.2 incidents
    
    # --- INJECTING ANOMALIES (The "Red Flags") ---
    
    # Red Flag 1: The Carbon Spike (5% of data)
    if random.random() < 0.05:
        carbon *= 10 
        
    # Red Flag 2: The Diversity Reporting Gap (Missing Data)
    if random.random() < 0.08:
        diversity = np.nan
        
    # Red Flag 3: The Sustainability Paradox (Impossible Zeroes)
    if industry == 'Manufacturing' and random.random() < 0.03:
        water = 0.0 

    data.append({
        'Supplier_ID': f'SUP-{1000+i}',
        'Company_Name': f'Vendor_{i}',
        'Industry': industry,
        'Region': random.choice(['APAC', 'EMEA', 'NA', 'LATAM']),
        'Carbon_Emissions_MT': round(carbon, 2),
        'Water_Usage_m3': round(water, 2),
        'Social_Diversity_Score_%': round(diversity, 2) if not np.isnan(diversity) else None,
        'Safety_Violations': safety_incidents,
        'Last_Audit_Date': (datetime.now() - timedelta(days=random.randint(0, 365))).strftime('%Y-%m-%d'),
        'Compliance_Status': 'Certified' # We will challenge this later
    })

# 3. Create DataFrame and Export
df = pd.DataFrame(data)
df.to_csv('E:/analytics/datasets_for_DA_proj_Self/esg-assure-compliance-engine/data/suppliers_raw.csv', index=False)

print(f"✅ Success! 'suppliers_raw.csv' generated with {num_suppliers} rows.")
print("🚨 Note: Anomalies have been injected. Your next task will be to find them.")

