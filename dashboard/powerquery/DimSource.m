let
    Source = #table(
        type table [Source = text, Source_Display = text],
        {
            {"Paper", "Paper Register"},
            {"EMR", "Electronic Medical Record"},
            {"DHIS2", "DHIS2"}
        }
    )
in
    Source
