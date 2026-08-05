import numpy as np
import pandas as pd

np.random.seed(42)

N_BATTERIES = 500
N_CYCLES = 1000
INITIAL_CAPACITY = 100.0
FAILURE_THRESHOLD = 70.0

rows = []
for battery_id in range(1, N_BATTERIES + 1):
    alpha = np.random.uniform(0.15, 0.35)
    capacity = INITIAL_CAPACITY
    failed = False
    rul_at_failure = None

    for cycle in range(1, N_CYCLES + 1):
        dod = np.random.uniform(0.6, 0.9)
        temp = np.random.uniform(20, 45)
        crate = np.random.uniform(0.5, 3.0)
        resistance = 1.5 + (cycle / N_CYCLES) * 3.5 + np.random.normal(0, 0.1)
        voltage_sag = 0.1 + (cycle / N_CYCLES) * 0.4 + np.random.normal(0, 0.02)
        ambient = np.random.uniform(15, 40)

        dod_factor = (dod - 0.6) / 0.3 * 0.3
        temp_factor = (temp - 20) / 25 * 0.2
        crate_factor = (crate - 0.5) / 2.5 * 0.15

        base_decay = alpha / N_CYCLES
        decay = base_decay * (1 + dod_factor + temp_factor + crate_factor)

        capacity = capacity * (1 - decay) + np.random.normal(0, 0.3)
        capacity = max(capacity, 0.0)

        if capacity < FAILURE_THRESHOLD and not failed:
            failed = True
            rul_at_failure = N_CYCLES - cycle

        rows.append({
            "battery_id": battery_id,
            "cycle_number": cycle,
            "depth_of_discharge": round(dod, 4),
            "avg_temperature": round(temp, 2),
            "charge_rate_c": round(crate, 4),
            "internal_resistance": round(resistance, 4),
            "capacity_ah": round(capacity, 4),
            "voltage_sag": round(voltage_sag, 4),
            "ambient_temp": round(ambient, 2),
            "is_failed": failed,
        })

df = pd.DataFrame(rows)
df.to_csv("data/dataset.csv", index=False)
print(f"Generated {len(df)} rows for {N_BATTERIES} batteries")
print(f"Failed batteries: {df['battery_id'][df['is_failed']].nunique()}")
print(f"Dataset saved to data/dataset.csv")