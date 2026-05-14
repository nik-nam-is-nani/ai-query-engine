"""
Visualization Recommender - Suggest charts based on data types
"""


def recommend_viz(columns, sample_rows):
    """
    Analyze column types and recommend visualizations.

    Args:
        columns: list of column names
        sample_rows: list of dict row samples

    Returns: { recommendations: [{ type, reason, config: { xKey, yKey, colorKey } }] }
    """
    recommendations = []

    if not sample_rows or not columns:
        return {"recommendations": [{"type": "table", "reason": "No data to visualize", "config": {}}]}

    # Analyze columns
    numeric_cols = []
    categorical_cols = []
    datetime_cols = []
    geo_cols = []

    for col in columns:
        col_lower = col.lower()

        # Check sample data for type inference
        sample_vals = [row.get(col) for row in sample_rows[:5] if row.get(col) is not None]

        if all(isinstance(v, (int, float)) for v in sample_vals if v):
            numeric_cols.append(col)
        elif all(isinstance(v, str) for v in sample_vals if v):
            # Check for datetime patterns
            import re
            if any(re.search(r'\d{4}-\d{2}-\d{2}', str(v)) for v in sample_vals if v):
                datetime_cols.append(col)
            # Check for geo
            elif any(x in col_lower for x in ["lat", "lon", "latitude", "longitude"]):
                geo_cols.append(col)
            elif any(x in col_lower for x in ["country", "city", "state", "region"]):
                geo_cols.append(col)
            else:
                categorical_cols.append(col)

    # Recommendation rules
    has_numeric = len(numeric_cols) > 0
    has_categorical = len(categorical_cols) > 0
    has_datetime = len(datetime_cols) > 0
    has_geo = len(geo_cols) > 0

    # Rule: 1 numeric + 1 categorical → bar or pie
    if has_numeric and has_categorical:
        recommendations.append({
            "type": "bar",
            "reason": f"Aggregate {numeric_cols[0]} by {categorical_cols[0]}",
            "config": {"xKey": categorical_cols[0], "yKey": numeric_cols[0], "colorKey": categorical_cols[0] if len(categorical_cols) > 1 else None}
        })
        recommendations.append({
            "type": "pie",
            "reason": f"Show distribution of {categorical_cols[0]}",
            "config": {"xKey": categorical_cols[0], "yKey": numeric_cols[0], "colorKey": categorical_cols[0]}
        })

    # Rule: 1 datetime + 1 numeric → line or area
    if has_datetime and has_numeric:
        recommendations.append({
            "type": "line",
            "reason": f"Show {numeric_cols[0]} trend over time",
            "config": {"xKey": datetime_cols[0], "yKey": numeric_cols[0], "colorKey": None}
        })
        recommendations.append({
            "type": "area",
            "reason": f"Cumulative {numeric_cols[0]} over time",
            "config": {"xKey": datetime_cols[0], "yKey": numeric_cols[0], "colorKey": None}
        })

    # Rule: Multiple numerics + 1 categorical → grouped bar or radar
    if len(numeric_cols) >= 2 and has_categorical:
        recommendations.append({
            "type": "grouped_bar",
            "reason": f"Compare metrics across {categorical_cols[0]}",
            "config": {"xKey": categorical_cols[0], "yKey": numeric_cols[0], "colorKey": numeric_cols[1] if len(numeric_cols) > 1 else None}
        })
        recommendations.append({
            "type": "radar",
            "reason": f"Multi-metric comparison for {categorical_cols[0]}",
            "config": {"xKey": categorical_cols[0], "yKey": numeric_cols[0], "colorKey": categorical_cols[0]}
        })

    # Rule: 1 column only → stat card
    if len(columns) == 1:
        recommendations.append({
            "type": "stat",
            "reason": "Single metric summary",
            "config": {"valueKey": columns[0]}
        })

    # Rule: 2 numerics → scatter
    if len(numeric_cols) >= 2:
        recommendations.append({
            "type": "scatter",
            "reason": f"Correlation between {numeric_cols[0]} and {numeric_cols[1]}",
            "config": {"xKey": numeric_cols[0], "yKey": numeric_cols[1], "colorKey": categorical_cols[0] if has_categorical else None}
        })

    # Rule: geographic column → map
    if has_geo:
        recommendations.append({
            "type": "map",
            "reason": f"Geographic visualization of {columns[0]}",
            "config": {"geoKey": geo_cols[0], "valueKey": numeric_cols[0] if has_numeric else columns[0]}
        })

    # Rule: 5 unique categorical values → horizontal bar
    unique_cats = 0
    if categorical_cols and sample_rows:
        sample_vals = [row.get(categorical_cols[0]) for row in sample_rows[:20] if row.get(categorical_cols[0]) is not None]
        unique_cats = len(set(sample_vals))

    if unique_cats == 5:
        recommendations.append({
            "type": "horizontal_bar",
            "reason": f"Compare 5 categories in {categorical_cols[0]}",
            "config": {"xKey": categorical_cols[0], "yKey": numeric_cols[0] if has_numeric else "count", "colorKey": None}
        })

    # Default to table if no specific recommendation
    if not recommendations:
        recommendations.append({
            "type": "table",
            "reason": "Default visualization for tabular data",
            "config": {}
        })

    return {"recommendations": recommendations}