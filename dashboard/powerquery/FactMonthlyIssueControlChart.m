let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/monthly_issue_control_chart.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types = Table.TransformColumnTypes(Headers, {
        {"Month", type date}, {"Records", Int64.Type},
        {"Issue_Records", Int64.Type}, {"Missing_Records", Int64.Type},
        {"Source_Discrepancy_Records", Int64.Type}, {"Outlier_Records", Int64.Type},
        {"Late_Records", Int64.Type}, {"Issue_Rate", type number},
        {"Centre_Line", type number}, {"Lower_Control_Limit", type number},
        {"Upper_Control_Limit", type number},
        {"Outside_Descriptive_Limits", type logical}, {"Control_Status", type text}
    }, "en-US"),
    MonthStart = Table.TransformColumns(
        Types, {{"Month", each Date.StartOfMonth(_), type date}}
    )
in
    MonthStart
