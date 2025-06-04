import pandas as pd
import random
import datetime

# Define end date and generate business days (last 180 working days)
end_date = datetime.date(2025, 5, 29)
business_days = []
current_date = end_date

while len(business_days) < 180:
    if current_date.weekday() < 5:  # Monday-Friday
        business_days.append(current_date)
    current_date -= datetime.timedelta(days=1)

business_days.reverse()

# Define client names and Minimum Transfer Amounts (MTA)
client_names = ["ClientA", "ClientB", "ClientC", "ClientD", "ClientE", "ClientF"]
client_MTAs = {
    "ClientA": 100000,
    "ClientB": 200000,
    "ClientC": 150000,
    "ClientD": 80000,
    "ClientE": 1200000,
    "ClientF": 2500000
}
interest_rate_range = (3.0, 6.0)

# Generate margin call data
margin_calls = []

for day_index, date in enumerate(business_days):
    for client in client_names:
        seed = hash(client) + date.day
        local_random = random.Random(seed)

        base_value = 3000000 + (hash(client) % 6) * 800000 + local_random.randint(100000, 500000)
        day_factor = day_index / len(business_days)
        trend_factor = (0.2 * (day_factor * 2) + 0.1)
        random_factor = 0.05 + local_random.random() * 0.15

        mtm = max(base_value * (1 + trend_factor + random_factor), 1000000)
        mtm = round(mtm)

        volatility = round(15 + (hash(client) % 6) * 3 + trend_factor * 10 + local_random.randint(1, 5))
        interest_rate = round(max(interest_rate_range[0] + (interest_rate_range[1] - interest_rate_range[0]) * 
                          (0.5 + trend_factor * 0.3 + local_random.random() * 0.2), 0.1), 1)

        mta = client_MTAs[client]

        shouldBeAboveMTA = local_random.random() > 0.4
        if shouldBeAboveMTA:
            target_margin_call_amount = mta * (1.0 + local_random.random() * 0.5)
        else:
            target_margin_call_amount = mta * (0.3 + local_random.random() * 0.6)

        total_deduction = mtm - target_margin_call_amount
        collateral_ratio = 0.7 + local_random.random() * 0.2
        collateral = round(total_deduction * collateral_ratio)
        threshold = round(total_deduction * (1 - collateral_ratio))

        collateral = max(collateral, 100000)
        threshold = max(threshold, 50000)

        margin_call_amount = mtm - collateral - threshold
        margin_call_made = "Yes" if margin_call_amount >= mta else "No"

        if margin_call_amount <= 0:
            margin_call_amount = 100000 + local_random.randint(10000, 50000)

        margin_calls.append([date.strftime("%d-%b-%Y"), client, mtm, collateral, threshold, volatility, "USD", 
                            interest_rate, mta, margin_call_made, margin_call_amount])

# Convert data to Pandas DataFrame and save as CSV
df = pd.DataFrame(margin_calls, columns=["Date", "Client", "MTM", "Collateral", "Threshold", "Volatility", "Currency", 
                                         "InterestRate", "MTA", "MarginCallMade", "MarginCallAmount"])

df.sort_values(by=["Date", "Client"], inplace=True)

df.to_csv("MarginCallData.csv", index=False)

print(f"Generated margin call test data for {len(margin_calls)} entries.")
print(f"Data covers {len(business_days)} business days for {len(client_names)} clients.")
print("Data saved to MarginCallData.csv")
