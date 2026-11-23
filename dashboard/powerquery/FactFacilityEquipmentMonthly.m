let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/facility_equipment_monthly_summary.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Facility_ID", type text}, {"Facility_Name", type text}, {"District", type text},
        {"Month", type date}, {"Active_Assets", Int64.Type}, {"Breakdown_Events", Int64.Type},
        {"Unplanned_Downtime_Hours", type number}, {"Planned_Maintenance_Downtime_Hours", type number},
        {"Total_Downtime_Hours", type number}, {"Mean_Service_Availability_Pct", type number},
        {"Mean_Operational_Uptime_Pct", type number}, {"PM_Due", Int64.Type},
        {"PM_Completed", Int64.Type}, {"PM_Overdue", Int64.Type},
        {"High_Risk_Assets", Int64.Type}, {"Maintenance_Cost_Credits", Int64.Type},
        {"PM_Completion_Pct", type number}, {"Synthetic_Data", type logical}
    })
in
    Typed
