let
    Source = Csv.Document(File.Contents(pWarehouseRoot & "/analytics/facility_infrastructure_profiles.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Facility_ID", type text}, {"Facility_Name", type text}, {"District", type text},
        {"Facility_Type", type text}, {"Urban_Rural", type text},
        {"Catchment_Population", Int64.Type}, {"Primary_Power_Configuration", type text},
        {"Primary_Water_Source", type text}, {"Connectivity_Modality", type text},
        {"Illustrative_Backup_Power_Hours", type number}, {"Illustrative_Water_Storage_Days", type number},
        {"Synthetic_Data", type logical}
    })
in
    Typed
