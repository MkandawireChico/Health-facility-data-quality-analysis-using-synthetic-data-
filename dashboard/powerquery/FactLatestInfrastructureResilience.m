let
    Source = Csv.Document(File.Contents(pWarehouseRoot & "/analytics/facility_latest_infrastructure_resilience.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Facility_ID", type text}, {"Facility_Name", type text}, {"District", type text},
        {"Month", type date}, {"Infrastructure_Resilience_Score", type number},
        {"Infrastructure_Risk_Band", type text}, {"Power_Availability_Pct", type number},
        {"Water_Availability_Pct", type number}, {"Connectivity_Availability_Pct", type number},
        {"Primary_Power_Configuration", type text}, {"Primary_Water_Source", type text},
        {"Connectivity_Modality", type text}, {"Synthetic_Data", type logical}
    })
in
    Typed
