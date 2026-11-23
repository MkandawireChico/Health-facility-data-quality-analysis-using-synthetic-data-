// Create a text parameter pWarehouseRoot pointing to data/warehouse.
let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/raw/facility_dimension.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types = Table.TransformColumnTypes(Headers, {
        {"Facility_ID", type text}, {"Facility_Name", type text},
        {"District", type text}, {"Facility_Type", type text},
        {"Urban_Rural", type text}, {"Ownership", type text},
        {"Catchment_Population", Int64.Type}, {"Is_Synthetic", type logical}
    }, "en-US"),
    UniqueKeys = Table.Distinct(Types, {"Facility_ID"})
in
    UniqueKeys
