// Power Query M — FactSourceObservation
// Create a text parameter named pStagedFactPath containing the full path to
// data/warehouse/staged/facility_reporting_staged.csv.

let
    Source = Csv.Document(
        File.Contents(pStagedFactPath),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    SelectedColumns = Table.SelectColumns(
        PromotedHeaders,
        {
            "Record_ID", "Facility_ID", "Month", "Programme", "Indicator",
            "Paper_Value", "EMR_Value", "DHIS2_Value"
        }
    ),
    TypedColumns = Table.TransformColumnTypes(
        SelectedColumns,
        {
            {"Record_ID", type text},
            {"Facility_ID", type text},
            {"Month", type date},
            {"Programme", type text},
            {"Indicator", type text},
            {"Paper_Value", type number},
            {"EMR_Value", type number},
            {"DHIS2_Value", type number}
        }
    ),
    AddedIndicatorKey = Table.AddColumn(
        TypedColumns,
        "Indicator_Key",
        each [Programme] & "|" & [Indicator],
        type text
    ),
    UnpivotedSources = Table.Unpivot(
        AddedIndicatorKey,
        {"Paper_Value", "EMR_Value", "DHIS2_Value"},
        "Source_Column",
        "Source_Value"
    ),
    RenamedSource = Table.TransformColumns(
        UnpivotedSources,
        {
            {
                "Source_Column",
                each Text.BeforeDelimiter(_, "_Value"),
                type text
            }
        }
    ),
    RenamedColumn = Table.RenameColumns(
        RenamedSource,
        {{"Source_Column", "Source"}}
    ),
    RemovedMissingValues = Table.SelectRows(
        RenamedColumn,
        each [Source_Value] <> null
    ),
    MonthStart = Table.TransformColumns(
        RemovedMissingValues,
        {{"Month", each Date.StartOfMonth(_), type date}}
    )
in
    MonthStart
