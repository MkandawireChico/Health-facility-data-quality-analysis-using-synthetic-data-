// Reference the loaded FactReporting query; do not load a second copy of the CSV.
let
    Selected = Table.SelectColumns(
        FactReporting,
        {"Record_ID", "Facility_ID", "Month", "Indicator_Key",
         "Paper_Value", "EMR_Value", "DHIS2_Value"}
    ),
    Unpivoted = Table.Unpivot(
        Selected,
        {"Paper_Value", "EMR_Value", "DHIS2_Value"},
        "Source_Field", "Source_Value"
    ),
    AddSource = Table.AddColumn(
        Unpivoted, "Source",
        each Text.BeforeDelimiter([Source_Field], "_Value"), type text
    ),
    RemoveHelper = Table.RemoveColumns(AddSource, {"Source_Field"}),
    KeepObserved = Table.SelectRows(RemoveHelper, each [Source_Value] <> null),
    Types = Table.TransformColumnTypes(KeepObserved, {
        {"Record_ID", type text}, {"Facility_ID", type text},
        {"Month", type date}, {"Indicator_Key", type text},
        {"Source", type text}, {"Source_Value", type number}
    }, "en-US")
in
    Types
