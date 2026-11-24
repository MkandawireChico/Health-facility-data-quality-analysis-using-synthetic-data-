let
    Source = Csv.Document(File.Contents(pWarehouseRoot & "/analytics/facility_monthly_workforce_capacity.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Facility_ID", type text}, {"Facility_Name", type text}, {"District", type text},
        {"Month", type date}, {"Illustrative_Establishment", Int64.Type}, {"Filled_Positions", Int64.Type},
        {"Vacant_Positions", Int64.Type}, {"Absent_Positions", Int64.Type},
        {"Available_On_Duty_Positions", Int64.Type}, {"Workforce_Coverage_Pct", type number},
        {"Absence_Rate_Pct", type number}, {"Estimated_Overtime_Hours", type number},
        {"Synthetic_Workload_Demand_Proxy", type number}, {"Weighted_Available_Capacity", type number},
        {"Workforce_Pressure_Index", type number}, {"Capacity_Proxy_Per_1000_Catchment", type number},
        {"Synthetic_Data", type logical}
    })
in
    Typed
