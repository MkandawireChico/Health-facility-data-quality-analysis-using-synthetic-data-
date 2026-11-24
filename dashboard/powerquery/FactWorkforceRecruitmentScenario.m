let
    Source = Csv.Document(File.Contents(pWarehouseRoot & "/analytics/workforce_recruitment_scenario.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Role", type text}, {"Required_Positions", Int64.Type}, {"Filled_Positions", Int64.Type},
        {"Vacancies", Int64.Type}, {"Cost_Per_Position", Int64.Type},
        {"Recruitment_Cost_Credits", Int64.Type}, {"Funded_Positions", Int64.Type},
        {"Unfunded_Positions", Int64.Type}, {"Budget_Credits_Available", Int64.Type},
        {"Budget_Credits_Unallocated", Int64.Type}
    })
in
    Typed
