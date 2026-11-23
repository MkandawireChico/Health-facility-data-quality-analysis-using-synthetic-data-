let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/facility_resource_capacity.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Facility_ID", type text}, {"Facility_Name", type text}, {"District", type text},
        {"Facility_Type", type text}, {"Urban_Rural", type text},
        {"Catchment_Population", Int64.Type}, {"Illustrative_Requirement_Units", Int64.Type},
        {"Synthetic_Available_Units", Int64.Type}, {"Baseline_Gap_Units", Int64.Type},
        {"Baseline_Capacity_Coverage_Pct", type number}
    })
in
    Typed
