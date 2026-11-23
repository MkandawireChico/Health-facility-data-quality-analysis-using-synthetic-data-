let
    Source = Csv.Document(File.Contents(pWarehouseRoot & "/analytics/infrastructure_upgrade_scenarios.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Facility_ID", type text}, {"Facility_Name", type text}, {"District", type text},
        {"Upgrade", type text}, {"Domain", type text}, {"Synthetic_Cost_Credits", Int64.Type},
        {"Baseline_Unserved_Interruption_Hours", type number},
        {"Illustrative_Avoided_Interruption_Hours", type number},
        {"Avoided_Hours_Per_100_Credits", type number},
        {"Selected_Package_For_Facility", type logical}, {"Within_Illustrative_Budget", type logical},
        {"Budget_Credits_Available", Int64.Type}, {"Budget_Credits_Unallocated", Int64.Type},
        {"Synthetic_Data", type logical}
    })
in
    Typed
