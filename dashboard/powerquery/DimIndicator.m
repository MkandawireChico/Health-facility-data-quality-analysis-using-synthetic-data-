let
    Source = Table.SelectColumns(FactReporting, {"Indicator_Key", "Programme", "Indicator"}),
    UniqueIndicators = Table.Distinct(Source, {"Indicator_Key"}),
    Sorted = Table.Sort(UniqueIndicators, {{"Programme", Order.Ascending}, {"Indicator", Order.Ascending}})
in
    Sorted
