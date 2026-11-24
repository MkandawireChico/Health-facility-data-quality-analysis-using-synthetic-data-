let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/monthly_indicator_target_attainment.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types = Table.TransformColumnTypes(Headers, {
        {"Month", type date}, {"Programme", type text}, {"Indicator", type text}, {"Indicator_Key", type text},
        {"reporting_records", Int64.Type}, {"valid_attainment_records", Int64.Type},
        {"reported_total", type number}, {"target_total", type number},
        {"facilities", Int64.Type}, {"attainment_pct", type number},
        {"performance_band", type text}, {"valid_data_pct", type number}
    }, "en-US")
in
    Types
