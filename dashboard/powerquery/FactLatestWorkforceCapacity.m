let
    Source = Csv.Document(File.Contents(pWarehouseRoot & "/analytics/facility_latest_workforce_capacity.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Facility_ID", type text}, {"Facility_Name", type text}, {"District", type text},
        {"Month", type date}, {"Workforce_Coverage_Pct", type number}, {"Workforce_Pressure_Index", type number},
        {"Vacant_Positions", Int64.Type}, {"Absent_Positions", Int64.Type},
        {"Workforce_Risk_Band", type text}, {"Catchment_Population", Int64.Type},
        {"Urban_Rural", type text}, {"Facility_Type", type text}, {"Synthetic_Data", type logical}
    })
in
    Typed
