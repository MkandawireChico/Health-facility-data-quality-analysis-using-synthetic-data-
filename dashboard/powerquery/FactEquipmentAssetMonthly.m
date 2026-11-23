let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/equipment_asset_monthly_performance.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Asset_ID", type text}, {"Facility_ID", type text}, {"Facility_Name", type text},
        {"District", type text}, {"Facility_Type", type text}, {"Urban_Rural", type text},
        {"Equipment_Type", type text}, {"Category", type text}, {"Criticality", type text},
        {"Month", type date}, {"Asset_Age_Years", type number}, {"Calendar_Hours", Int64.Type},
        {"Breakdown_Count", Int64.Type}, {"Unplanned_Downtime_Hours", type number},
        {"Planned_Maintenance_Downtime_Hours", type number}, {"Total_Downtime_Hours", type number},
        {"Service_Availability_Pct", type number}, {"Operational_Uptime_Pct", type number},
        {"Preventive_Maintenance_Due", type logical}, {"Preventive_Maintenance_Completed", type logical},
        {"Preventive_Maintenance_Overdue", type logical}, {"Condition_Score", type number},
        {"Maintenance_Cost_Credits", Int64.Type}, {"Equipment_Risk_Score", type number},
        {"Risk_Band", type text}, {"Synthetic_Data", type logical}
    })
in
    Typed
