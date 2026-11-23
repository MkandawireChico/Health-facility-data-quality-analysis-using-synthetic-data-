let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/equipment_maintenance_work_orders.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Work_Order_ID", type text}, {"Asset_ID", type text}, {"Facility_ID", type text},
        {"Facility_Name", type text}, {"District", type text}, {"Equipment_Type", type text},
        {"Month", type date}, {"Work_Order_Type", type text}, {"Priority", type text},
        {"Status", type text}, {"Due_Date", type date}, {"Downtime_Hours", type number},
        {"Cost_Credits", Int64.Type}, {"Synthetic_Data", type logical}
    })
in
    Typed
