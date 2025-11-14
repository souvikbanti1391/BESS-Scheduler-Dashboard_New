import pandas as pd
import numpy as np
from pulp import LpProblem, LpVariable, lpSum, LpMaximize, LpStatus

def run_scheduler(df, bess_power_mw, bess_energy_mwh, horizon_days):
    # Simple heuristic scheduler using pulp (hourly)
    # Convert bess params to MW and MWh as given; assume 1 MW = 1 MW
    # For demo, create schedule that charges on low price hours and discharges on high price hours
    df = df.sort_values('timestamp').reset_index(drop=True)
    n = len(df)
    # simplify: decide charge/discharge per hour within +/- bess_power_mw
    df['action_mw'] = 0.0
    # heuristic: charge when mcp below median, discharge when above median
    median = df['mcp'].median() if 'mcp' in df.columns else 0.0
    for i,row in df.iterrows():
        if row['mcp'] < median/1.0:
            df.at[i,'action_mw'] = -min(bess_power_mw, bess_energy_mwh)  # charge negative
        else:
            df.at[i,'action_mw'] = min(bess_power_mw, bess_energy_mwh)   # discharge positive
    # compute SOC (naive)
    soc = []
    cap = bess_energy_mwh
    current = cap/2.0
    for a in df['action_mw']:
        current = max(0, min(cap, current - a/ (1.0) * 1.0))  # simplistic
        soc.append(current)
    df['soc_mwh'] = soc
    return df[['timestamp','mcp','action_mw','soc_mwh']]
