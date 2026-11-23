let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/cold_chain_expiry_risk_summary.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Facility_ID", type text}, {"Facility_Name", type text}, {"District", type text},
        {"Month", type date}, {"Commodity_ID", type text}, {"Commodity", type text},
        {"Programme", type text}, {"Demand_Units", Int64.Type},
        {"Fulfilled_Consumption_Units", Int64.Type}, {"Unmet_Demand_Units", Int64.Type},
        {"Expired_Units", Int64.Type}, {"Closing_Stock_Units", Int64.Type},
        {"Near_Expiry_30_Day_Units", Int64.Type}, {"Near_Expiry_60_Day_Units", Int64.Type},
        {"Near_Expiry_90_Day_Units", Int64.Type}, {"Days_To_Nearest_Expiry", Int64.Type},
        {"Temperature_Excursion_Days", Int64.Type}, {"Estimated_Excursion_Hours", Int64.Type},
        {"Temperature_Data_Coverage_Pct", type number}, {"Temperature_Data_Status", type text},
        {"Temperature_Excursion_Flag", type logical}, {"Expiry_Risk_Share_Pct", type number},
        {"Cold_Chain_Risk_Score", type number}, {"Risk_Band", type text},
        {"Synthetic_Data", type logical}
    })
in
    Typed
