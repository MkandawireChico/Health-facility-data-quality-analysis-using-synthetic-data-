let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/facility_equipment_asset_register.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Asset_ID", type text}, {"Facility_ID", type text}, {"Facility_Name", type text},
        {"District", type text}, {"Facility_Type", type text}, {"Urban_Rural", type text},
        {"Equipment_Type", type text}, {"Category", type text}, {"Criticality", type text},
        {"Install_Date", type date}, {"Age_At_Start_Years", type number},
        {"Expected_Life_Years_Assumption", Int64.Type}, {"PM_Interval_Months_Assumption", Int64.Type},
        {"Synthetic_Replacement_Cost_Credits", Int64.Type}, {"Initial_Condition_Score", type number},
        {"Asset_Status", type text}, {"Synthetic_Data", type logical}
    })
in
    Typed
