let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/facility_commodity_batch_ledger.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Batch_ID", type text}, {"Facility_ID", type text}, {"Facility_Name", type text},
        {"District", type text}, {"Commodity_ID", type text}, {"Commodity", type text},
        {"Programme", type text}, {"Unit", type text}, {"Synthetic_Supplier_ID", type text},
        {"Manufacture_Date", type date}, {"Receipt_Date", type date}, {"Receipt_Month", type text},
        {"Expiry_Date", type date}, {"Month", type date}, {"Opening_Stock_Units", Int64.Type},
        {"Receipts_Units", Int64.Type}, {"Fulfilled_Consumption_Units", Int64.Type},
        {"Expired_Units", Int64.Type}, {"Closing_Stock_Units", Int64.Type},
        {"Days_To_Expiry_At_Month_End", Int64.Type}, {"Near_Expiry_30_Days", type logical},
        {"Near_Expiry_60_Days", type logical}, {"Near_Expiry_90_Days", type logical},
        {"Temperature_Excursion_Days", Int64.Type}, {"Temperature_Excursion_Flag", type logical},
        {"Temperature_Data_Status", type text}, {"Synthetic_Unit_Cost_Credits", Int64.Type},
        {"Synthetic_Data", type logical}
    })
in
    Typed
