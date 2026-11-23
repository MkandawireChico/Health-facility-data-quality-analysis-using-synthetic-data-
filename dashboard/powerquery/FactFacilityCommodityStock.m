let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/facility_commodity_stock_ledger.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Facility_ID", type text}, {"Facility_Name", type text}, {"District", type text},
        {"Month", type date}, {"Commodity_ID", type text}, {"Commodity", type text},
        {"Programme", type text}, {"Unit", type text},
        {"Opening_Stock_Units", Int64.Type}, {"Receipts_Units", Int64.Type},
        {"Demand_Units", Int64.Type}, {"Fulfilled_Consumption_Units", Int64.Type},
        {"Unmet_Demand_Units", Int64.Type}, {"Closing_Stock_Units", Int64.Type},
        {"Stockout_Days", Int64.Type}, {"Stockout_Flag", type logical},
        {"Synthetic_Data", type logical}
    })
in
    Typed
