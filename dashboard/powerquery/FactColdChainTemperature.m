let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/facility_cold_chain_temperature_monitoring.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Sensor_ID", type text}, {"Facility_ID", type text}, {"Facility_Name", type text},
        {"District", type text}, {"Month", type date}, {"Days_In_Month", Int64.Type},
        {"Observed_Days", Int64.Type}, {"Temperature_Data_Coverage_Pct", type number},
        {"Mean_Temperature_C", type number}, {"Minimum_Temperature_C", type number},
        {"Maximum_Temperature_C", type number}, {"Excursion_Days", Int64.Type},
        {"Estimated_Excursion_Hours", Int64.Type}, {"Temperature_Excursion_Flag", type logical},
        {"Temperature_Data_Status", type text}, {"Synthetic_Data", type logical},
        {"Assumed_Minimum_Temperature_C", type number}, {"Assumed_Maximum_Temperature_C", type number}
    })
in
    Typed
