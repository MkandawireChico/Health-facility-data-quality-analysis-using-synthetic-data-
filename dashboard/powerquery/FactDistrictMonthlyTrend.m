let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/district_monthly_quality_trends.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types = Table.TransformColumnTypes(Headers, {
        {"District", type text}, {"Month", type date},
        {"records", Int64.Type}, {"facilities", Int64.Type},
        {"detected_issue_records", Int64.Type}, {"missing_records", Int64.Type},
        {"source_discrepancy_records", Int64.Type}, {"outlier_records", Int64.Type},
        {"late_records", Int64.Type}, {"detected_issue_rate_pct", type number}
    }, "en-US"),
    MonthStart = Table.TransformColumns(
        Types, {{"Month", each Date.StartOfMonth(_), type date}}
    )
in
    MonthStart
