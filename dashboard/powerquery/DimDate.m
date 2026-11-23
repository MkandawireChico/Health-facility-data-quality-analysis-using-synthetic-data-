let
    Months = List.Transform(List.Distinct(FactReporting[Month]), each Date.StartOfMonth(_)),
    FirstMonth = List.Min(Months),
    LastMonth = List.Max(Months),
    MonthCount = (Date.Year(LastMonth) - Date.Year(FirstMonth)) * 12
        + Date.Month(LastMonth) - Date.Month(FirstMonth) + 1,
    MonthStarts = List.Transform(
        {0..MonthCount - 1},
        each Date.AddMonths(FirstMonth, _)
    ),
    TableFromMonths = Table.FromList(MonthStarts, Splitter.SplitByNothing(), {"MonthStart"}),
    Types = Table.TransformColumnTypes(TableFromMonths, {{"MonthStart", type date}}),
    AddYear = Table.AddColumn(Types, "Year", each Date.Year([MonthStart]), Int64.Type),
    AddQuarter = Table.AddColumn(AddYear, "Quarter", each "Q" & Text.From(Date.QuarterOfYear([MonthStart])), type text),
    AddMonthNumber = Table.AddColumn(AddQuarter, "MonthNumber", each Date.Month([MonthStart]), Int64.Type),
    AddMonthName = Table.AddColumn(AddMonthNumber, "MonthName", each Date.MonthName([MonthStart]), type text),
    AddYearMonth = Table.AddColumn(AddMonthName, "YearMonth", each Date.ToText([MonthStart], "yyyy-MM"), type text)
in
    AddYearMonth
