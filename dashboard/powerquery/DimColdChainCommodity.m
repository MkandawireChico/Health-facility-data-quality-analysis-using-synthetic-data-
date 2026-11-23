let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/cold_chain_catalog.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Commodity_ID", type text}, {"Commodity", type text}, {"Programme", type text},
        {"Unit", type text}, {"Monthly_Demand_per_10000", Int64.Type},
        {"Shelf_Life_Days", Int64.Type}, {"Synthetic_Unit_Cost_Credits", Int64.Type}
    })
in
    Typed
