let
    Source = Csv.Document(File.Contents(pWarehouseRoot & "/analytics/equipment_infrastructure_association.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Power_Interruption_Band", type text}, {"Facility_Months", Int64.Type},
        {"Mean_Unserved_Power_Hours", type number}, {"Mean_Operational_Uptime_Pct", type number},
        {"Mean_Resilience_Score", type number}, {"Interpretation", type text}
    })
in
    Typed
