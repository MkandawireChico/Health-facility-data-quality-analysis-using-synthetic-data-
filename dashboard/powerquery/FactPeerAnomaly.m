let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/statistical_peer_anomalies.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types = Table.TransformColumnTypes(OperationalOnly, {
        {"Record_ID", type text}, {"Facility_ID", type text},
        {"Month", type date}, {"District", type text},
        {"Programme", type text}, {"Indicator", type text},
        {"Reported_Value", type number}, {"Statistical_Anomaly", type logical},
        {"Statistical_Anomaly_Score", type number},
        {"Statistical_Method", type text}, {"Peer_Group_Size", Int64.Type}
    }, "en-US"),
    AnomaliesOnly = Table.SelectRows(Types, each [Statistical_Anomaly] = true),
    AddIndicatorKey = Table.AddColumn(
        AnomaliesOnly, "Indicator_Key",
        each [Programme] & "|" & [Indicator], type text
    )
in
    AddIndicatorKey
