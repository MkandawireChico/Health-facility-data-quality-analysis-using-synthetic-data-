let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/equipment_catalog.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Equipment_Type", type text}, {"Category", type text}, {"Criticality", type text},
        {"Base_Monthly_Failure_Probability", type number}, {"PM_Interval_Months", Int64.Type},
        {"Expected_Life_Years", Int64.Type}, {"Synthetic_Replacement_Cost_Credits", Int64.Type}
    })
in
    Typed
