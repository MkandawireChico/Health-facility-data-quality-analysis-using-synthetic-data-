let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/detector_evaluation_metrics.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types = Table.TransformColumnTypes(Headers, {
        {"defect", type text}, {"true_positive", Int64.Type},
        {"false_positive", Int64.Type}, {"false_negative", Int64.Type},
        {"true_negative", Int64.Type}, {"precision", type number},
        {"recall", type number}, {"f1", type number},
        {"specificity", type number}, {"false_positive_rate", type number},
        {"accuracy", type number}, {"support", Int64.Type},
        {"predicted_positive", Int64.Type}
    }, "en-US")
in
    Types
