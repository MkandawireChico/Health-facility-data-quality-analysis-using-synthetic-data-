let
    Source = Csv.Document(
        File.Contents(pWarehouseRoot & "/analytics/commodity_replenishment_plan.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Facility_ID", type text}, {"Facility_Name", type text}, {"District", type text},
        {"Commodity_ID", type text}, {"Commodity", type text}, {"Programme", type text},
        {"Snapshot_Month", type date}, {"Closing_Stock_Units", Int64.Type},
        {"Average_Monthly_Demand_Units", type number}, {"Estimated_Days_of_Cover", type number},
        {"Target_Stock_Units", Int64.Type}, {"Requested_Replenishment_Units", Int64.Type},
        {"Synthetic_Unit_Cost_Credits", Int64.Type}, {"Requested_Cost_Credits", Int64.Type},
        {"Recent_Stockout_Days", Int64.Type}, {"Priority_Score", type number},
        {"Allocated_Replenishment_Units", Int64.Type}, {"Allocated_Cost_Credits", Int64.Type},
        {"Unfunded_Replenishment_Units", Int64.Type}, {"Post_Allocation_Stock_Units", Int64.Type},
        {"Post_Allocation_Days_of_Cover", type number}
    })
in
    Typed
