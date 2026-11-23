let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/commodity_catalog.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Commodity_ID", type text}, {"Commodity", type text}, {"Programme", type text},
        {"Unit", type text}, {"Monthly_Demand_per_10000", Int64.Type},
        {"Synthetic_Unit_Cost_Credits", Int64.Type}, {"Essentiality_Weight", type number}
    })
in
    Typed
