let
    Source = Csv.Document(File.Contents(pWarehouseRoot & "/analytics/facility_workforce_establishment.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Facility_ID", type text}, {"Facility_Name", type text}, {"District", type text},
        {"Facility_Type", type text}, {"Urban_Rural", type text}, {"Role", type text},
        {"Illustrative_Establishment", Int64.Type}, {"Baseline_Filled_Positions", Int64.Type},
        {"Baseline_Vacancies", Int64.Type}, {"Workforce_Weight", type number},
        {"Synthetic_Recruitment_Cost_Credits_Per_Position", Int64.Type}, {"Synthetic_Data", type logical}
    })
in
    Typed
