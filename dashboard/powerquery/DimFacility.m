// Power Query M — DimFacility
// Create a text parameter pFacilityDimensionPath containing the full path to
// data/warehouse/raw/facility_dimension.csv.

let
    Source = Csv.Document(
        File.Contents(pFacilityDimensionPath),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    TypedColumns = Table.TransformColumnTypes(
        PromotedHeaders,
        {
            {"Facility_ID", type text},
            {"Facility_Name", type text},
            {"District", type text},
            {"Facility_Type", type text},
            {"Urban_Rural", type text},
            {"Ownership", type text},
            {"Catchment_Population", Int64.Type},
            {"Is_Synthetic", type logical}
        },
        "en-US"
    ),
    UniqueFacilityKeys = Table.Distinct(TypedColumns, {"Facility_ID"})
in
    UniqueFacilityKeys
