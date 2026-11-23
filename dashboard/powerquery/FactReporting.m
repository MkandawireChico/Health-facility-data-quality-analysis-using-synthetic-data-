// Create a text parameter pWarehouseRoot pointing to data/warehouse.
let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/staged/facility_reporting_staged.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    GroundTruthColumns = List.Select(
        Table.ColumnNames(Headers),
        each Text.StartsWith(_, "Ground_Truth_")
    ),
    OperationalOnly = Table.RemoveColumns(Headers, GroundTruthColumns, MissingField.Ignore),
    TypedColumns = Table.TransformColumnTypes(OperationalOnly, {
        {"Record_ID", type text}, {"Facility_ID", type text},
        {"Facility", type text}, {"District", type text},
        {"Month", type date}, {"Programme", type text}, {"Indicator", type text},
        {"Reported_Value", type number}, {"Target_Value", type number},
        {"Data_Source", type text}, {"Paper_Value", type number},
        {"EMR_Value", type number}, {"DHIS2_Value", type number},
        {"Submission_Date", type date}, {"Deadline_Date", type date},
        {"Quality_Missing_Reported_Value", type logical},
        {"Quality_Source_Discrepancy", type logical},
        {"Quality_Late_Submission", type logical},
        {"Quality_Insufficient_Source_Count", type logical},
        {"Quality_Source_Spread", type number},
        {"Quality_Invalid_Numeric_Count", Int64.Type},
        {"Quality_Negative_Value_Count", Int64.Type},
        {"Quality_Invalid_Source_Label", type logical},
        {"Quality_Missing_Submission_Date", type logical},
        {"Quality_Missing_Deadline_Date", type logical},
        {"Structural_Error_Count", Int64.Type}
    }, "en-US"),
    MonthStart = Table.TransformColumns(
        TypedColumns, {{"Month", each Date.StartOfMonth(_), type date}}
    ),
    AddIndicatorKey = Table.AddColumn(
        MonthStart, "Indicator_Key",
        each [Programme] & "|" & [Indicator], type text
    ),
    AddOperationalOutlier = Table.AddColumn(
        AddIndicatorKey, "Operational_Detected_Outlier",
        each if [Target_Value] = null or [Target_Value] <= 0 or [Reported_Value] = null
             then false else [Reported_Value] / [Target_Value] > 1.5,
        type logical
    )
in
    AddOperationalOutlier
