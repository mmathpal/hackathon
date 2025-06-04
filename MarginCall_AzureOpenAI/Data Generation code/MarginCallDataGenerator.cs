using System;
using System.Collections.Generic;
using System.Globlization;
using System.IO;
using System.Linq;

namespace MarginCallDataGenerator
{
    class Program
    {
        static void Main(string[] args)
        {
            DateTime endDate = new DateTime(2025, 5, 29); //Example date

            var businessDays = new List<Datetime>();
            DateTime currentDate = endDate;

            while (businessDays.Count < 180)
            {
                if (currentDate.DayOfWeek != DayOfWeek.Saturday && currentDate.DayOfWeek != DayOfWeek.Sunday)
                {
                    businessDays.Add(currentDate);
                }
                currentDate = currentDate.AddDays(-1);
            }

            //Reverse to get chronological order
            businessDays.Reverse();

            //Define client names
            var clientNames = new[] { "ClientA", "ClientB", "ClientC", "ClientD", "ClientE", "ClientF" };

            var clientMTAs = new Dictionary<string, double>
            {
                { "ClientA", 100000},
                { "ClientB", 200000},
                { "ClientC", 150000},
                { "ClientD", 80000},
                { "ClientE", 1200000},
                { "ClientF", 2500000}
            };

            var interestRateRange = (Min: 3.0, Max: 6.0);

            var random = new Random(42);
            var marginCalls = new List<MarginCallData>();

            for (int dayIndex = 0; dayIndex < businessDays.Count; dayIndex++)
            {
                DateTime date = businessDays[dayIndex];

                foreach (var client in clientNames)
                {
                    int seed = client.GetHashCode() + date.DayOfYear;
                    var localRandom = new Random(seed);

                    double baseValue = 3000000 + (client.GetHashCode() % 6) * 800000 + localRandom.Next(100000, 500000);

                    double dayFactor = (double)dayIndex / businessDays.Count;
                    double trendFactor = Math.Sin(dayFactor * Math.PI * 2) * 0.2 + 0.1;
                    double randomFactor = 0.05 + localRandom.NextDouble() * 0.15; //Always positive random factor

                    //Calculate MTM with trend and randomness (ensure  non-zero)
                    double mtm = Math.Max(baseValue * (1 + trendFactor + randomFactor), 1000000);
                    mtm = Math.Round(mtm, 0);

                    //volatility varies by client
                    double volatility = 15 + (client.GetHashCode() % 6) * 3 + trendFactor * 10 + localRandom.Next(1, 5);
                    volatility = Math.Round(volatility, 0);

                    //Interest rate with small daily
                    double interestRate = Math.Max(interestRateRange.Min + (interestRateRange.Max - interestRateRange.Min) * (0.5 + trendFactor * 0.3 + localRandom.NextDouble() * 0.2), 0.1);
                    interestRate = Math.Round(interestRate, 1);

                    double mta = clientMTAs[client];

                    var marginCall = new MarginCallData
                    {
                        Date = date,
                        Client = client,
                        MTM = mtm,
                        Currency = "USD",
                        Volatility = volatility,
                        InterestRate = interestRate,
                        MTA = mta
                    };

                    bool shouldBeAboveMTA = localRandom.NextDouble() > 0.4;

                    if (shouldBeAboveMTA)
                    {
                        double targetMarginCallAmount = mta * (1.0 + localRandom.NextDouble() * 0.5);
                        double totalDeduction = mtm - targetMarginCallAmount;
                        double collateralRatio = 0.7 + localRandom.NextDouble() * 0.2;
                        marginCall.Collateral = Math.Round(totalDeduction * collateralRatio, 0);
                        marginCall.Threshold = Math.Round(totalDeduction * (1 - collateralRatio), 0);

                        marginCall.Collateral = Math.Max(marginCall.Collateral, 100000);
                        marginCall.Threshold = Math.Max(marginCall.Threshold, 50000);

                        double calculateAmount = mtm - marginCall.Collateral - marginCall.Threshold;
                        if (calculateAmount < mta)
                        {
                            marginCall.Collateral = Math.Max(mtm - mta - marginCall.Threshold, 100000);
                        }
                        marginCall.MarginCallAmount = mtm - marginCall.Collateral - marginCall.Threshold;
                        marginCall.MarginCallMade = marginCall.MarginCallAmount >= mta ? "Yes" : "No";
                    }
                    else
                    {
                        double targetMarginCallAmount = mta * (0.3 + localRandom.NextDouble() * 0.6);
                        double totalDeduction = mtm - targetMarginCallAmount;
                        double collateralRatio = 0.7 + localRandom.NextDouble() * 0.2;
                        marginCall.Collateral = Math.Round(totalDeduction * collateralRatio, 0);
                        marginCall.Threshold = Math.Round(totalDeduction * (1 - collateralRatio), 0);

                        marginCall.Collateral = Math.Max(marginCall.Collateral, 100000);
                        marginCall.Threshold = Math.Max(marginCall.Threshold, 50000);

                        double calculatedAmount = mtm - marginCall.Collateral - marginCall.Threshold;

                        if (calculatedAmount >= mta)
                        {
                            marginCall.Collateral = Math.Max(mtm - 100000 - marginCall.Threshold, 100000);
                        }
                        else if (calculatedAmount <= 0)
                        {
                            marginCall.Collateral = Math.Max(mtm - 100000 - marginCall.Threshold, 100000);
                        }

                        marginCall.MarginCallAmount = mtm - marginCall.Collateral - marginCall.Threshold;
                        marginCall.MarginCallMade = marginCall.MarginCallAmount >= mta ? "Yes" : "No";
                    }

                    if (marginCall.MarginCallAmount <= 0)
                    {
                        marginCall.MarginCallAmount = 100000 + localRandom.Next(10000, 50000);
                    }

                    marginCall.Add(marginCall);
                }
            }

            marginCalls = marginCalls
            .OrderBy(m => m.Date)
            .ThenBy(m => m.Client)
            .ToList();

            //Write to Csv
            using (var writer = new StreamWriter("MarginCallData.csv"))
            {
                writer.WriteLine("Date,Client,MTM,Collateral,Threshold,Volatility,Currency,InterestRate,MTA,MarginCallMade,MarginCallAmount");

                foreach (var call in marginCalls)
                {
                    writer.WriteLine($"{call.Date.ToString("dd-MMM-yyyy", CultureInfo.InvariantCulture)}," +
                                      $"{call.Client}," +
                                      $"{call.mtm}," +
                                      $"{call.Collateral}," +
                                      $"{call.Threshold}," +
                                      $"{call.Volatility}," +
                                      $"{call.Currency}," +
                                      $"{call.InterestRate}," +
                                      $"{call.MTA}," +
                                      $"{call.MarginCallMade}," +
                                      $"{call.MarginCallAmount}"
                                     );
                }
            }

            Console.WriteLine($"Generated margin call test dat for {marginCalls.Count} entries.")
            Console.WriteLine($"Data covers {businessDays.Count} business days for {clientNames.Length} clients.");
            Console.WriteLine("Data saved to MarginCallData.csv");
        }
    }

    public class MarginCallData
    {
        public DateTime Date { get; set; }
        public string Client { get; set; }
        public double MTM { get; set; }
        public double Collateral { get; set; }
        public double Threshold { get; set; }
        public double Volatility { get; set; }
        public string Currency { get; set; }
        public double InterestRate { get; set; }
        public double MTA { get; set; }
        public string MarginCallMade { get; set; }
        public double MarginCallAmount { get; set; }

    }
}