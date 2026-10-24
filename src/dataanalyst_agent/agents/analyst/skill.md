# Plotly Data Visualization Standards & Patterns

## 1. Chart Type Selection Matrix
- **Category vs Metric:** Horizontal Bar (`px.bar(orientation='h')`). Sort descending so the top value is at the top.
- **Time Trend:** Line (`px.line`). Convert dates with `pd.to_datetime(..., errors='coerce')`.
- **Distribution:** Histogram (`px.histogram(..., nbins=30)`) or Box Plot (`px.box`). If rows > 400, sample with `df.sample(min(400, len(df)), random_state=42)`.
- **Two Metrics (Correlation):** Scatter (`px.scatter`). If rows > 400, sample with `df.sample(min(400, len(df)), random_state=42)`.
- **Composition / Share:** Donut chart (`px.pie(..., hole=0.4)`), ONLY if <= 5 categories. Otherwise, use horizontal bar.

## 2. Clean Data Transformations
- **Handle Dates Safely:**
  ```python
  df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
  df = df.dropna(subset=[date_col])
  ```
- **Collapse Long Categories:** If a categorical column has >12 unique values, keep the top 10 and group the rest into `"Other"`:
  ```python
  top10 = df['category'].value_counts().nlargest(10).index
  df['category'] = df['category'].where(df['category'].isin(top10), other='Other')
  ```
- **Ensure Sorting:** For horizontal bars, sort ascending in DataFrame so the largest bar appears at the top:
  ```python
  df = df.sort_values(by=val_col, ascending=True)
  ```

## 3. Visual Styling & Polish
- Always use `template="plotly_white"`.
- **Insightful Titles:** The chart title must state the conclusion or finding (e.g. *"Fiber Optic has the highest churn rate at 42%"* instead of *"Churn by InternetService"*).
- **Benchmark Lines:** When computing an average or target benchmark, add a reference line:
  ```python
  fig.add_hline(y=avg_val, line_dash="dash", line_color="gray", annotation_text=f"Avg: {avg_val:.1f}")
  ```
- **Layout & Margins:**
  ```python
  fig.update_layout(
      height=450,
      margin=dict(l=40, r=40, t=60, b=40)
  )
  ```

## 4. Hard Prohibitions
- NEVER call `fig.show()`.
- NEVER call `print()`.
- NEVER use 3D plots (`scatter3d`, `surface`).