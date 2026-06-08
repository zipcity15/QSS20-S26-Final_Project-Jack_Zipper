# Aid, Displacement, and Violence in the DRC: An analysis how aid impacts IDP flows in the Eastern DRC and how violence has impacted patterns of aid spending.
### Jack Zipper's Final Project for QSS 20

[Google Drive link for data here](https://drive.google.com/drive/folders/1uCD0Pz8TyrORPHGUJoKdhrBjs3u54un1)

---

## Guiding Question

In the eastern region of the Democratic Republic of the Congo, a region rocked by the resurgence of the M23 insurgency, how does the introduction of aid influence flows of internally displaced persons (IDPs) in the region? Nationally, how has violence impacted patterns of aid spending? To what extent does aid respond to violence at the local level in the DRC?

---

# Methodology

## Pipeline Overview

The eleven scripts run sequentially in the order listed. The diagram below shows how data flows between them.

```
Raw IATI CSV + Admin shapefiles
        │
        ▼
  00_IATI_cleaning  ──────────────────────────────────────────────────────────┐
        │ iati-drc-cleaned.csv                                                │
        ▼                                                                     │
  01_IDP_cleaning                                                             │
  (OCHA xlsx files)                                                           │
        │ departees_eastern_drc.csv                                           │
        │ returnees_eastern_drc.csv                                           │
        │ idp_dat_eastern_drc.csv                                             │
        ▼                                                                     │
  02_aid_displacement_merge ◄─────────────────────────────────────────────── ┤
        │ aid_displacement_merged.csv                                         │
        ▼                                                                     │
  03_aid_displacement_regression                                              │
        │ aid_displacement_regression.png                                     │
                                                                              │
  04_displacement_analysis (reads departees/returnees CSVs directly)         │
        │ idp_net_flow_monthly.png                                            │
        │ displaced_returnees_by_province.png                                 │
        │ displacement_causes_top10.png                                       │
        │ displacement_summary_stats.png                                      │
                                                                              │
  05_conflict_data_cleaning                                                   │
  (ACLED HRP xlsx files — political violence + civilian targeting)            │
        │ conflict_dat_cleaned.csv                                            │
        ▼                                                                     │
  06_conflict_aid_merge ◄──────────────────────────────────────────────────── ┘
        │ violence_aid_merged.csv
        ▼
  07_aid_violence_scatter ──► scatter_conflict_aid.png
  08_aid_violence_regression ──► violence_aid_regression.png / .txt
  09_choropleth_map ──► drc_choropleth_start.png / drc_choropleth_end.png / .gif / drc_quarterly_metric.csv
        │ drc_quarterly_metric.csv
        ▼
  10_time_underserved_regression ──► underserved_trend.png / underserved_regression.png
```

Shared helper functions (`fill_deaths`, `assign_admin_level`, and project-wide path constants) live in utils.py and are imported by the notebooks that need them.

---

## utils.py — Shared Module

**Location:** [code/utils.py](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/code/utils.py)

All notebooks that need shared logic import from this file via:
```python
import sys; sys.path.insert(0, '/Users/jackzipper/QSS20/final_project/code')
from utils import fill_deaths, assign_admin_level, SMALL_CONSTANT, EASTERN_PROVINCES
```
Note that not all functions are put in utils.py. Most functions are defined at the top of each notebook. Only logic that is genuinely shared across multiple notebooks — `fill_deaths` (used by scripts 07 and 09) and `assign_admin_level` (used twice in script 00) — was moved to utils.py to avoid duplication. Notebook-specific functions remain defined at the top of the notebook where they are used.

**Constants:**
| Name | Value | Purpose |
|------|-------|---------|
| `SMALL_CONSTANT` | `0.5` | Floor substituted for zero-death months after 6+ consecutive zeros (prevents `log(0)`). |
| `EASTERN_PROVINCES` | `['Nord-kivu', 'Sud-kivu', 'Ituri']` | Canonical province list used to filter OCHA data. Lowercase-k matches OCHA source spellings. |
| `PROJECT_ROOT` | `Path('.../final_project')` | Root path for the project. |
| `DATA_DIR` | `PROJECT_ROOT / 'final_project_data'` | Input data directory. |
| `OUT_DIR` | `PROJECT_ROOT / 'output'` | Output directory for figures and CSVs. |

**Functions:**

- **`fill_deaths(series)`** — Death-fill imputation applied per-town on the `total_deaths` column. Carries forward the last observed non-zero death count for up to 5 consecutive zero months; substitutes `SMALL_CONSTANT = 0.5` after 6+ consecutive zeros or at the series start. Results stored in `deaths_filled` (raw `total_deaths` is not modified). Used by scripts 07 and 09.

- **`assign_admin_level(gdf_points, boundaries, name_col, max_distance_m=55_000)`** — Point-in-polygon spatial join with a nearest-neighbour fallback. Runs `gpd.sjoin(..., predicate='within')` first; unmatched points are passed to `gpd.sjoin_nearest` with a 55 km distance cap. Returns a Series of admin name strings (NaN where truly outside DRC). Used by script 00 for both Admin-1 and Admin-2 assignment.

---

## Order to Run

### 1. [00_IATI_cleaning.ipynb](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/code/00_IATI_cleaning.ipynb)

**Packages:** `pandas`, `geopandas`, utils.py

**Input data:**
- [iati-activity-locations-in-democratic-republic-of-the-congo.csv](https://drive.google.com/file/d/1lo-Pedx_OcgNwm4YNmWbhoMqWIOmNGpa/view?usp=drive_link) — IATI aid activity records for the DRC from the Humanitarian Data Exchange (HDX). Each row is one geocoded aid activity with fields including: `aid` (project identifier), `location_longitude` / `location_latitude` (point coordinates), `day_start` / `day_end` (project dates), `spend` (USD disbursement), and `description`.
- [cod_admin_boundaries.shp/cod_admin1.shp](https://drive.google.com/file/d/1W3aOJXuyvs_mM93G-dXae_p3jZ32Ad1Z/view?usp=drive_link) — Admin-1 province polygons for all 26 DRC provinces (HDX COD boundary dataset).
- [cod_admin_boundaries.shp/cod_admin2.shp](https://drive.google.com/file/d/11LfIWN80UPoHo3AZuAvzmRxloK-XU-Gj/view?usp=drive_link) — Admin-2 territory polygons.

**Cleaning steps:**
1. All geometries are reprojected to EPSG:32635 (meters-based) for accurate distance calculations.
2. **Admin-1 assignment** — `assign_admin_level()` (from utils.py) runs a left spatial join (`predicate='within'`) to assign each aid point to a province. Points that fall outside all polygons (border edge cases) are caught by a nearest-neighbor fallback: `gpd.sjoin_nearest` with `max_distance=55,000` metres. Points still unmatched after both passes (i.e., genuinely outside DRC) are dropped.
3. **Admin-2 assignment** — the same `assign_admin_level()` function is called a second time with the Admin-2 boundary layer. The Admin-2 name column is auto-detected from a candidate list to handle shapefile inconsistencies across environments.
4. **Deduplication** — exact duplicate rows are dropped first. Then rows are deduplicated on the key columns `['aid', 'province_name', 'day_start', 'day_end', 'description', 'spend']` to handle cases where the same project appears at multiple coordinates within a province. This retains one row per unique project-province-period combination.

**Key note on join strategy:** All spatial joins use exact geometric matches (point-in-polygon) with a distance-based nearest-neighbor fallback — not fuzzy string matching. Province name strings are not used as the join key here; geometry is.

**Output:** [iati-drc-cleaned.csv](https://drive.google.com/file/d/1gwdMcWSfxQDt1TNnN-apsLRiFQa2P_A6/view?usp=sharing) (4,917 rows; 2,836 unique aid projects; 26 provinces; 148 Admin-2 units)

---

### 2. [01_IDP_cleaning.ipynb](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/code/01_IDP_cleaning.ipynb)

**Packages:** `pandas`, `os`, `re`

**Input data:**
- [ocha_monthly_departures/](https://drive.google.com/drive/folders/1NLRIQNovCWeF_fFrpD_ETHwfdK1y_wn5?usp=drive_link) — directory of monthly `.xlsx` snapshots from OCHA tracking displacement departure events. Each file covers one month; each row is one displacement event recording fields including `id` (event identifier), `movement_date`, `person` (people displaced), `cause_label`, `admin1_label` (province), and `admin2_label`.
- [ocha_monthly_returnees/](https://drive.google.com/drive/folders/1ePZzNn9P5DOidYD1ahUGLYKGeuXZpPIH?usp=drive_link) — identical structure for return movements.

**Cleaning steps:**
1. **Version deduplication** — files ending in `__1_.xlsx` are treated as superseded versions; if both `foo.xlsx` and `foo__1_.xlsx` exist, `foo.xlsx` is skipped.
2. **Snapshot month extraction** — the month is parsed from the filename using a French month-name dictionary (e.g., `'janvier'→'01'`) combined with a 4-digit year regex, inside `extract_snapshot_month()`.
3. **Sheet detection** — `get_sheet_name()` checks a prioritised list of 18 candidate sheet names to handle inconsistent Excel formatting across files.
4. **Column filtering** — only the 13 columns in `usecols` are loaded via `load_files()`; files missing `admin1_label` or `person` are skipped.
5. **Temporal filter** — inside `build_province_panel()` → `filter_and_dedup()`: rows are retained only where `movement_date` falls within the same year and month as the file's snapshot month. This prevents events recorded late from being double-counted across snapshots.
6. **Event deduplication** — rows are deduplicated on `id` alone, keeping the earliest snapshot appearance. Each physical displacement event should appear exactly once.
7. **Province filter** — only `['Nord-kivu', 'Sud-kivu', 'Ituri']` are retained. Note: these spellings are lowercase-k, matching the OCHA source; 02_aid_displacement_merge.ipynb maps these to the IATI capitalisation.
8. **Panel aggregation** — `build_province_panel()` groups events by `['admin1_label', 'snapshot_month']` and sums to produce `total_displaced` / `total_returnees` and unique site counts.
9. **Panel merge** — the displacement and returnee panels are merged with an **outer join** on `['admin1_label', 'snapshot_month']` so that months with departures but no returnees (and vice versa) are retained; NaNs are filled with 0.

**Variable definitions:**
- `total_displaced` — sum of `person` across all departure events in a province-month.
- `total_returnees` — sum of `person` across all return events in a province-month.
- `net_monthly_flow` = `total_displaced` − `total_returnees`: positive = net outward displacement; negative = net return.

**Outputs:** [departees_eastern_drc.csv](https://drive.google.com/file/d/1kOsBAcxX9Rggl_hNRpQzrJLPTbIjQ3_4/view?usp=drive_link), [returnees_eastern_drc.csv](https://drive.google.com/file/d/1FnkMgswunkkrivcyzaXED5-ObT7g6aMa/view?usp=drive_link), [idp_dat_eastern_drc.csv](https://drive.google.com/file/d/1tceOJ3baq0-77X8cAsu3vlZa6JRHLd1l/view?usp=drive_link)

**Note on saved CSVs:** departees_eastern_drc.csv and returnees_eastern_drc.csv contain the raw concatenated event-level rows for **all provinces** (before province filtering). The eastern-province filter is re-applied independently by 04_displacement_analysis.ipynb when it reads these files directly.

---

### 3. [02_aid_displacement_merge.ipynb](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/code/02_aid_displacement_merge.ipynb)

**Packages:** `pandas`, `numpy`

**Input data:**
- [idp_dat_eastern_drc.csv](https://drive.google.com/file/d/1tceOJ3baq0-77X8cAsu3vlZa6JRHLd1l/view?usp=drive_link) — output of script 01
- [iati-drc-cleaned.csv](https://drive.google.com/file/d/1gwdMcWSfxQDt1TNnN-apsLRiFQa2P_A6/view?usp=drive_link) — output of script 00

**Cleaning / prep steps:**
1. Province names in the IATI data are standardised to match OCHA capitalisation via exact string replacement: `{'Nord-Kivu':'Nord-kivu', 'Sud-Kivu':'Sud-kivu', 'Ituri':'Ituri'}` (applied in `NAME_MAP`). This is an **exact match** on province name strings; no fuzzy matching is used.
2. IATI data is filtered to the three eastern provinces.
3. A monthly spend rate is computed for each project inside `compute_monthly_spend()`: `monthly_spend = spend / (day_length / 30.44)`, where `day_length` is project duration in days. Projects with zero duration are assigned `monthly_spend = 0`.

**Merge strategy (`build_aid_panel()`):**
The merge proceeds in two steps, both using **exact matches** on `['admin1_label', 'snapshot_month']` (province name string + date):

Step 1: A **left join** cross-joins the IDP panel's province-month keys against the IATI project table on province name (`admin1_label` = `location_name`). This produces one row per (IDP observation × IATI project in that province).

Step 2: Two separate aggregations are computed from this crossed table:
- `new_project_monthly_spend` / `new_project_count` — projects whose `day_start` falls within the prior 6-month window before the snapshot month.
- `total_active_monthly_spend` / `total_active_projects` — projects where `day_start ≤ snapshot_month` and `day_end ≥ snapshot_month`.

Both aggregations are merged back onto the IDP panel via **left joins** on `['admin1_label', 'snapshot_month']`; unmatched months receive 0. An assertion confirms the row count does not change after the merge.

**Variable definitions:**
- `new_project_monthly_spend` — sum of `monthly_spend` for all projects starting in the 6 months prior to the snapshot month, in the same province (USD/month).
- `total_active_monthly_spend` — sum of `monthly_spend` for all projects active (ongoing) during the snapshot month (USD/month).
- `log_new_project_spend` = `log1p(new_project_monthly_spend)`.
- `log_total_active_spend` = `log1p(total_active_monthly_spend)`. `log1p` is used so that zero-spend months map to 0 rather than −∞.

**Output:** [aid_displacement_merged.csv](https://drive.google.com/file/d/1Q1NMYft8mfj2y7zeKhPXQPAeyS-tiNdQ/view?usp=drive_link)

---

### 4. [03_aid_displacement_regression.ipynb](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/code/03_aid_displacement_regression.ipynb)

**Packages:** `pandas`, `numpy`, `matplotlib`, `linearmodels`, `statsmodels`

**Input data:** [aid_displacement_merged.csv](https://drive.google.com/file/d/1Q1NMYft8mfj2y7zeKhPXQPAeyS-tiNdQ/view?usp=drive_link)

**Model specification (fitted in `make_regression_table()`):**

```
net_monthly_flow_{it} = α_i + β₁·log_new_project_spend_{it} + β₂·log_total_active_spend_{it} + ε_{it}
```

where *i* indexes province and *t* indexes snapshot month. `α_i` is a province fixed effect (`entity_effects=True`). Standard errors are heteroskedasticity-robust (`cov_type='robust'`). No time fixed effects are included (`time_effects=False`).

**Variable definitions:**
- `net_monthly_flow` (dependent) — persons displaced minus persons returned in province *i* in month *t* (constructed in 01_IDP_cleaning.ipynb). Positive values indicate net outward displacement.
- `log_new_project_spend` — log(1 + sum of monthly spend rates for projects that started in the prior 6 months), measuring the *flow* of new aid into a province.
- `log_total_active_spend` — log(1 + sum of monthly spend rates for all currently active projects), measuring the *stock* of ongoing aid.

**Source of identification:** Identification relies on within-province variation over time (province fixed effects absorb all time-invariant provincial characteristics). The key assumption is that, conditional on province fixed effects, month-to-month variation in aid spending is not driven by contemporaneous shocks to displacement that are unobserved. This assumption is unlikely to hold perfectly — aid may be endogenously directed toward displacement crises — which motivates the lagged-violence analysis in script 08. This analysis should therefore be interpreted as descriptive/associational rather than causal.

**This is not a predictive analysis** — no train-test split or cross-validation is used.

**Output:** [aid_displacement_regression.png](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/output/aid_displacement_regression.png)

---

### 5. [04_displacement_analysis.ipynb](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/code/04_displacement_analysis.ipynb)

**Packages:** `pandas`, `numpy`, `matplotlib`

**Input data:** [departees_eastern_drc.csv](https://drive.google.com/file/d/1kOsBAcxX9Rggl_hNRpQzrJLPTbIjQ3_4/view?usp=drive_link), [returnees_eastern_drc.csv](https://drive.google.com/file/d/1FnkMgswunkkrivcyzaXED5-ObT7g6aMa/view?usp=drive_link) (outputs of script 01)

**Cleaning steps (`load_and_clean()`):** Reloads the raw event-level data and re-applies cleaning: filters to movement dates within the snapshot month, deduplicates on event `id`, filters to eastern provinces, and translates French cause labels to English via exact string replacement in `CAUSE_TRANSLATIONS`. Three encoding variants of "Amélioration des conditions" are mapped to a single English label.

**Outputs:** [idp_net_flow_monthly.png](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/output/idp_net_flow_monthly.png), [displaced_returnees_by_province.png](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/output/displaced_returnees_by_province.png), [displacement_causes_top10.png](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/output/displacement_causes_top10.png), [displacement_summary_stats.png](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/output/displacement_summary_stats.png)

---

### 6. [05_conflict_data_cleaning.ipynb](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/code/05_conflict_data_cleaning.ipynb)

**Packages:** `pandas`

**Input data:**
- [democratic-republic-of-congo_hrp_political_violence_events_and_fatalities_by_month-year_as-of-0.xlsx](https://docs.google.com/spreadsheets/d/17E6CEwa431JKAtNhBPaEqBmv0vbmU1Vy/edit?usp=drive_link&ouid=118293876790289471777&rtpof=true&sd=true) — ACLED political violence events and fatalities aggregated by Admin-2 territory and month. 66,364 rows × 10 columns; one row per territory-month.
- [democratic-republic-of-congo_hrp_civilian_targeting_events_and_fatalities_by_month-year_as-of-0.xlsx](https://docs.google.com/spreadsheets/d/1SAqUgGpmbwV6CbR724-QliWGDorEWn10/edit?usp=drive_link&ouid=118293876790289471777&rtpof=true&sd=true) — ACLED civilian targeting events and fatalities, same structure and identical territory-month keys.

**Cleaning steps:**
1. Read the `Data` sheet from both files (skipping the `TOU` licensing sheet).
2. Sum `Events` and `Fatalities` across the two violence categories (political violence + civilian targeting) for each territory-month.
3. Filter to 2021–2026.
4. **Name harmonisation:** 25 ACLED Admin-2 units are sub-territory cities (e.g., Bunia, Baraka, Kolwezi) not present in the COD shapefile. These represent ~5% of fatalities and are remapped to their parent COD Admin-2 territory via a manual lookup table (e.g., Baraka → Fizi, Bunia → Djugu, Kamituga → Mwenga). After remapping, events and fatalities are re-aggregated to the territory × month level.
5. Build `date_start` (first day of the month) and `year_month` (period string) columns from the `Month` and `Year` fields.

**Variable definitions:**
- `town_admin2` — COD Admin-2 territory name (after city-to-territory remapping).
- `violent_incidents` — total ACLED events (political violence + civilian targeting) in the territory-month.
- `total_deaths` — total ACLED fatalities (political violence + civilian targeting) in the territory-month.
- `date_start` — first calendar day of the month (for date filtering in downstream scripts).
- `year_month` — period string (e.g., `'2021-03'`) used as the panel join key.

**Output:** [conflict_dat_cleaned.csv](https://drive.google.com/file/d/1PcO33sd_H5-4inRf4tRHGB7IPdVvIl9e/view?usp=drive_link)

---

### 7. [06_conflict_aid_merge.ipynb](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/code/06_conflict_aid_merge.ipynb)

**Packages:** `pandas`, `numpy`

**Input data:**
- [iati-drc-cleaned.csv](https://drive.google.com/file/d/1gwdMcWSfxQDt1TNnN-apsLRiFQa2P_A6/view?usp=drive_link) — output of script 00
- [conflict_dat_cleaned.csv](https://drive.google.com/file/d/1PcO33sd_H5-4inRf4tRHGB7IPdVvIl9e/view?usp=drive_link) — output of script 05

**Merge strategy — three-step exact match on `['admin2_name', 'year_month']`:**

Step 1 — Balanced grid (`build_balanced_grid()`): The universe of Admin-2 units is taken as the union of all `town_admin2` values in the conflict data and all `admin2_name` values in the IATI data (after dropping NAs). A full Cartesian product of these 146 units × 72 months (2021-01 through 2026-12) produces a 10,512-row balanced panel. This ensures that admin2-month cells with no conflict *and* no aid receive true zeros rather than being absent.

Step 2 — Conflict pass-through (`aggregate_conflict()`): Because the ACLED data from script 05 is already aggregated to territory × month, this function simply renames `town_admin2` → `admin2_name` and selects the `violent_incidents` and `total_deaths` columns — no groupby is needed.

Step 3 — Aid aggregation with fractional spend (`build_aid_monthly()`): Each IATI project is expanded across every calendar month it overlaps with the 2021–2026 window using a vectorized cross-join (no row-by-row loop). For month *m*, the fractional spend allocated is:

```
fractional_spend = (active_days_in_month / total_project_days) × total_spend
```

where `total_project_days = (day_end − day_start).days`, clipped to a minimum of 1; `active_days_in_month` is the number of days the project overlapped with month *m*, computed vectorially via `max(day_start, month_start)` and `min(day_end, month_end)`. This allocation ensures the sum of fractional spend across all months equals the project's total spend. The expanded rows are aggregated by `['admin2_name', 'year_month']` to produce `num_aid_projects` (unique aid IDs) and `total_aid_spend` (sum of fractional spend).

Step 4 — Final merge (`merge_onto_grid()`): Both aggregations are left-joined onto the balanced grid; unmatched cells receive 0. An assertion confirms the row count equals the grid size.

**Key note on name matching:** The join between conflict data and IATI data uses exact string matching on `admin2_name`. Both datasets were assigned Admin-2 names from the *same* shapefile (cod_admin2.shp) in their respective cleaning scripts, so name strings should align. No fuzzy matching is applied; any Admin-2 unit present in only one dataset still appears in the panel (with zeros for the absent source) because the union of both Admin-2 name sets defines the grid.

**Variable definitions:**
- `violent_incidents` — number of conflict events recorded in admin2 unit *i* in month *t*.
- `total_deaths` — sum of ACLED fatalities in admin2 unit *i* in month *t*.
- `num_aid_projects` — count of distinct IATI project IDs with any fractional activity in admin2 unit *i* in month *t*.
- `total_aid_spend` — sum of fractional USD spend allocated to admin2 unit *i* in month *t* based on project overlap.

**Output:** [violence_aid_merged.csv](https://drive.google.com/file/d/1MiG9g8XdU-cZEvYpKw9TiqrHG9fkpi2d/view?usp=drive_link) (10,512 rows: 146 admin2 units × 72 months)

---

### 8. [07_aid_violence_scatter.ipynb](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/code/07_aid_violence_scatter.ipynb)

**Packages:** `pandas`, `numpy`, `matplotlib`, `adjustText`, utils.py

**Input data:** [violence_aid_merged.csv](https://drive.google.com/file/d/1MiG9g8XdU-cZEvYpKw9TiqrHG9fkpi2d/view?usp=drive_link)

**Processing steps:**

1. **Death-fill imputation (`fill_deaths()` from utils.py):** For each town, zero-death months are imputed as follows: if the streak of consecutive zero-death months is fewer than 6, the last observed non-zero death count is carried forward; if the streak reaches 6 or more, or if no prior non-zero value exists, the small constant `0.5` is used. This prevents log(0) = −∞ in the efficiency metric while preserving the signal from persistent conflict. The raw `total_deaths` column is not modified; results are stored in `deaths_filled`.

2. **Town-level aggregation (`build_town_averages()`):** For each town, sum `total_aid_spend` and `deaths_filled` across all months, then divide by the number of months observed to get per-month averages (`avg_aid_pm`, `avg_deaths_pm`).

3. **Efficiency metric:**
   ```
   metric = log1p(avg_aid_pm) − log1p(avg_deaths_pm)
   ```
   Both aid and deaths use `log1p` (log(1 + x)) so that zero values map to 0 rather than −∞ or negative numbers. Higher values indicate more aid spend per death (better served); lower values indicate less aid per death (underserved).

4. **Categorisation (`categorize_towns()`, vectorised with `np.select`):**
   - *Underserved*: `metric ≤ 25th percentile` of the metric distribution across all towns.
   - *Overserved*: `metric ≥ 75th percentile` **AND** `log1p(avg_aid_pm) ≥ 75th percentile` of log aid — i.e., high metric driven by genuinely high aid, not just absence of deaths.
   - *Other*: all remaining towns.

**Variable definitions:**
- `log_aid` = `log1p(avg_aid_pm)` — log(1 + average monthly aid spend) per town (USD).
- `log_deaths` = `log1p(avg_deaths_pm)` — log(1 + average monthly death-fill-imputed deaths) per town. Using `log1p` ensures all values are ≥ 0; towns with no deaths score 0 on the x-axis rather than a negative number.
- `metric` = `log_aid − log_deaths` — log aid-to-death ratio; the town-level efficiency score.

**Output:** [scatter_conflict_aid.png](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/output/scatter_conflict_aid.png)

---

### 9. [08_aid_violence_regression.ipynb](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/code/08_aid_violence_regression.ipynb)

**Packages:** `pandas`, `numpy`, `matplotlib`, `linearmodels`

**Input data:** [violence_aid_merged.csv](https://drive.google.com/file/d/1MiG9g8XdU-cZEvYpKw9TiqrHG9fkpi2d/view?usp=drive_link)

**Processing steps:**

1. Log transforms:
   - `log_aid_spend` = `log(total_aid_spend + 1)`
   - `log_deaths` = `log(total_deaths + 1)`

   Note: unlike script 7, **no death-fill imputation is applied** here. Zero-death months map to `log(0+1) = 0`, which is informative (no deaths that month).

2. Lag columns: Within each town, `log_deaths` is shifted by 1, 3, and 6 months to create `log_deaths_lag1`, `log_deaths_lag3`, `log_deaths_lag6`.

**Model specification (`run_twfe()`):**

Three separate models, one per lag:

```
log_aid_spend_{it} = α_i + γ_t + β·log_deaths_lag_k_{it} + ε_{it}
```

where *i* = Admin-2 town, *t* = month, `α_i` = town fixed effect, `γ_t` = month fixed effect (two-way FE), and *k* ∈ {1, 3, 6}. Standard errors are clustered by town (`cov_type='clustered', cluster_entity=True`).

**Source of identification:** The two-way fixed effects design identifies β from within-town, within-month variation — i.e., deviations from a town's average aid spending that co-move with deviations from that town's average lagged death toll, after removing common month-level shocks. The lag structure (1, 3, 6 months) probes whether aid responds to *past* violence rather than contemporaneous crisis, which would be more consistent with a causal interpretation. However, reverse causality (aid anticipating future violence) and omitted time-varying town-level confounders remain threats to causal identification. Results should be interpreted as evidence of a systematic association, not a clean causal estimate.

**This is not a predictive analysis** — no train-test split or cross-validation is used.

**Outputs:** [violence_aid_regression.txt](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/output/violence_aid_regression.txt), [violence_aid_regression.png](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/output/violence_aid_regression.png)
   * I created a .txt file because previously it was allowing me to export as a .png and I had to manually convert. The .txt file is an
     artifact of this and is the exact same thing as the .png version.  

---

### 10. [09_choropleth_map.ipynb](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/code/09_choropleth_map.ipynb)

**Packages:** `pandas`, `geopandas`, `numpy`, `matplotlib`, utils.py

**Input data:** [violence_aid_merged.csv](https://drive.google.com/file/d/1MiG9g8XdU-cZEvYpKw9TiqrHG9fkpi2d/view?usp=drive_link), [cod_admin_boundaries.shp/cod_admin2.shp](https://drive.google.com/file/d/11LfIWN80UPoHo3AZuAvzmRxloK-XU-Gj/view?usp=drive_link), [cod_admin_boundaries.shp/cod_admin1.shp](https://drive.google.com/file/d/1W3aOJXuyvs_mM93G-dXae_p3jZ32Ad1Z/view?usp=drive_link)

**Processing steps:**

1. **Death-fill imputation** — `fill_deaths()` imported from utils.py (same function as script 7; shared via utils to ensure identical behavior).

2. **Quarterly aggregation:** Monthly panel rows are grouped by `['admin2_name', 'quarter']` (calendar quarter), summing `total_aid_spend` and `deaths_filled`.

3. **Quarterly efficiency metric:**
   ```
   metric = log1p(quarterly_aid_spend) − log(max(quarterly_deaths_filled, 0.5))
   ```

4. **Choropleth join (`make_static()`):** The Admin-2 shapefile is merged with the quarterly metric via a **left join** on `adm2_name` (shapefile) = `admin2_name` (panel), using **exact string matching**. Territories with no panel match are shown as light gray ("no data").

5. **Color scale:** A 9-bin quantile-based `BoundaryNorm` is applied so each color band covers an equal share of the metric distribution. Dark crimson = low log($/death) = underserved; light yellow = high log($/death) = overserved.

**Intermediate output saved for downstream use:** [drc_quarterly_metric.csv](https://drive.google.com/file/d/1-UVxxe9oJNCPKoF3BtaTCfpohM89nKTw/view?usp=drive_link) — one row per (admin2, quarter) with `aid_spend`, `deaths_filled`, `log_aid`, `log_deaths`, and `metric`.

**Outputs:**
- [drc_quarterly_metric.csv](https://drive.google.com/file/d/1-UVxxe9oJNCPKoF3BtaTCfpohM89nKTw/view?usp=drive_link) — quarterly efficiency metric, read by script 10.
- [drc_choropleth_start.png](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/output/drc_choropleth_start.png) — static choropleth for the **first quarter of the analysis** (2021 Q1), providing a baseline snapshot of aid efficiency across DRC territories.
- [drc_choropleth_end.png](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/output/drc_choropleth_end.png) — static choropleth for the **last quarter of the analysis** (2026 Q4), showing how the distribution of aid efficiency has shifted over the study period.
- [drc_choropleth.gif](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/output/drc_choropleth.gif) — animated choropleth cycling through all 24 quarters (2021 Q1 – 2026 Q4) at 2 fps. Both static images use the same color scale as the GIF so they are directly comparable.

---

### 11. [10_time_underserved_regression.ipynb](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/code/10_time_under-served_regression.ipynb)

**Packages:** `pandas`, `numpy`, `matplotlib`, `scipy`, `statsmodels`

**Input data:** [drc_quarterly_metric.csv](https://drive.google.com/file/d/1-UVxxe9oJNCPKoF3BtaTCfpohM89nKTw/view?usp=drive_link) — output of script 09

**Processing steps:**

1. **Underserved classification:** A territory-quarter is classified as underserved if its `metric` is at or below the 25th percentile of the metric computed across *all* territory-quarters (a fixed global threshold). This threshold is computed once and held constant, so the count of underserved territories is comparable across time.

2. **Time-series aggregation:** For each quarter, sum the underserved indicator to get `n_underserved` (count) and mean it to get `pct_underserved` (share). A sequential integer index `t` (0, 1, 2, …) is constructed as the independent variable.

3. **OLS trend models:**
   ```
   n_underserved_t   = α + β·t + ε_t
   pct_underserved_t = α + β·t + ε_t
   ```
   Both are simple OLS regressions of the quarterly aggregate on the time index, testing whether the number/share of underserved territories has a statistically significant linear trend over the study period.

4. **Mann-Kendall test:** A non-parametric Kendall's τ test assesses monotonic trend without assuming normality. This complements the OLS test.

5. **Structural break analysis:** The series is split at quarter index `t = 16` (2025 Q1), corresponding to the Trump inauguration and USAID funding freeze. Separate OLS trend models are fit on the pre-break (`t < 16`) and post-break (`t ≥ 16`) subsamples using `trend_line()` / `eval_trend()` helpers. Trend lines are evaluated at continuous date ranges — spanning from the left edge of the first bar to the right edge of the last bar in each segment — and meet exactly at the break date for visual continuity.

**Variable definitions:**
- `metric` — quarterly log(aid/death) efficiency score for each territory-quarter, carried over from 09_choropleth_map.ipynb.
- `underserved` — binary indicator: 1 if `metric ≤ global 25th percentile`, 0 otherwise.
- `n_underserved` — count of underserved territory-quarters per quarter.
- `pct_underserved` — share of all territories classified as underserved in a given quarter.
- `t` — integer quarter index (0 = 2021 Q1, 1 = 2021 Q2, …); used as the time regressor.

**Source of identification:** This is a descriptive time-series trend analysis, not a causal model. The OLS slope on `t` estimates the average linear change in underservice per quarter. The structural break at 2025 Q1 is chosen *a priori* based on the known policy event (USAID freeze), not data-driven, which avoids pre-testing bias but means the break date is an assumption. A statistically significant post-break acceleration would be consistent with — but not proof of — a policy effect, since other concurrent shocks (e.g., escalating M23 conflict) could explain the same pattern.

**This is not a predictive analysis** — no train-test split or cross-validation is used.

**Outputs:** [underserved_trend.png](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/output/underserved_trend.png), [underserved_regression.png](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/output/underserved_regression.png)
