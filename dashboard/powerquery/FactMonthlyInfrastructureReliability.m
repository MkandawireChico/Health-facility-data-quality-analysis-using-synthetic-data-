let
    Source = Csv.Document(File.Contents(pWarehouseRoot & "/analytics/facility_monthly_infrastructure_reliability.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Facility_ID", type text}, {"Facility_Name", type text}, {"District", type text},
        {"Month", type date}, {"Calendar_Hours", Int64.Type},
        {"Power_Interruption_Events", Int64.Type}, {"Power_Interruption_Hours", type number},
        {"Backup_Power_Hours_Provided", type number}, {"Unserved_Power_Interruption_Hours", type number},
        {"Water_Interruption_Events", Int64.Type}, {"Water_Shortage_Hours", type number},
        {"Water_Buffered_Hours", type number}, {"Unserved_Water_Shortage_Hours", type number},
        {"Connectivity_Interruption_Events", Int64.Type}, {"Connectivity_Downtime_Hours", type number},
        {"Power_Availability_Pct", type number}, {"Water_Availability_Pct", type number},
        {"Connectivity_Availability_Pct", type number}, {"Infrastructure_Resilience_Score", type number},
        {"Synthetic_Data", type logical}
    })
in
    Typed
