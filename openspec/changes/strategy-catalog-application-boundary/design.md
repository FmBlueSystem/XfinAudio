# Strategy Catalog Application Boundary Design

Add `xfinaudio.application.strategy_catalog` with frozen `StrategyCatalogEntry`, `list_strategy_catalog()`, and `describe_strategy()`.
`BuildViewModel` maps application entries into its UI `StrategyOption` DTO and delegates explanations to application.
