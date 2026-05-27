# Aid and Displacement in the Eastern DRC: How aid impacts IDP flows. 
Jack Zipper's Final Project for QSS 20

# Guiding Question:
In the eastern region of the Democratic Republic of the Congo, a region rocked by the resurgence of the M23 insurgency, how does the introduction of aid influence flows of internally displaced persons (IDPs) in the region?

# Methods
Ordinary least squares regression. Dependent variable: net monthly displacement flows per province per month. 
Independent variables: log of new project monthly spend (treatment variable) and log of total active monthly spend (control).
Province fixed effects, excluded time fixed effects, and used robust standard errors 

# Order to Run
1. [00_IATI_Cleaning.ipynb]([url](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/code/00_IATI_Cleaning.ipynb))
   * Packages needed:
     * pandas as pd, geopandas
   * Data:
     * [iati-activity-locations-in-democratic-republic-of-the-congo.csv]([url](https://drive.google.com/file/d/11Y_PXmlMZQ_6jZbFkXMOF-D0Hyt6PVXh/view?usp=drive_link))
        * Data set from the Humanitarian Data Exchange (HDX) that details the aid and
          development activities in the DRC, as tracked by the International Aid Transparency Ini-
          tiative. This data set contains information on each aid/development project given in a
          certain area. Among the most relevant things for my analysis, it gives the date the aid
          intervention started (start day), how long it lasted in days (day length), the spend on the
          project in multiple currencies, though I just used USD (spend), the province the project took
          place in (location name), and the longitude and latitude of where the aid was deployed (lo-
          cation longitude and location latitude respectively).
     * [cod_admin_boundaries.shp/cod_admin1.shp]([url](https://drive.google.com/file/d/1RTTVl2CXENtgTihjgz1mbI5FzHuVfYGA/view?usp=drive_link)) in [cod_admin_boundaries.shp/]([url](https://drive.google.com/drive/folders/144ZmuXDYvrKyIgvfni3bn3UiUugAkhgY?usp=drive_link))
        * Administrative maps of the DRC, specifically from the Democratic Republic of the Congo -
          Subnational Administrative Boundaries dataset from HDX. These contained shape files of the adminis-
          trative borders of the DRC’s 26 provinces. Using the coordinates of each aid activity, put
          the aid activity into a certain province if it fell within its borders.
   * Workflow:
     * Clean and standardize data. A part of this was to determine the location of each aid activity
       which we did by looking at the longitude and latitude of each aid activity and then placing that
       in a certain province based on the coordinates of the borders of province. Duplicate rows are
       dropped, both in the form of exact duplicates and duplicates dropped on key columns (the same aid
       project may have multiple different coordinates associated with it, so there is additional logic
       to deal with this).
   * Output
     * Outputs newly cleaned and standardized data as [iati-drc-cleaned.csv]([url](https://drive.google.com/file/d/1TZnA1IfYYDwzBSzfgx-7eOlnrBvtRA7Y/view?usp=drive_link))  

2. [01_IDP_Cleaning.ipynb]([url](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/code/01_IDP_Cleaning.ipynb))
   * Packages needed:
     * pandas, os, re
   * Data:
     * [ocha_monthly_departures/]([url](https://drive.google.com/drive/folders/1cu6adkTvPH5eOcgsbY5IcI4-9DV0ojym?usp=drive_link))
        * Directory of excel spreadsheets that include data on a monthly snapshot of all active IDP displacement sites in the DRC.
        * Important rows include id, a unique site identifier, movement_date, the date the of displacement, household number of households
          displaced at site, and person, the number of individuals displaced at that site.
     * [ocha_monthly_returnees/]([url](https://drive.google.com/drive/folders/1AyrQVB5Rmv4aPHW9MhCKYaUGOf8ZI99g?usp=drive_link))
        * Same structure as the departures directory but tracking returnees instead of IDPs, where a returnee is one who has returned home
   * Workflow:
     * Defines the two folder paths, the list of eastern provinces we care about, a dictionary mapping French month names to
       numbers (since the filenames use French and are inconsistent), and the list of columns we want to load from each Excel file .
     * Creates functions to facilitate loading in the series of monthly sheets:
        * Extracts string of filename of each excel sheet in the directory so we can find the name of the month in French and
          map the month and year to each excel sheet (extract_snapshot_month()).
        * Take an opened sheet and find the tab in the sheet that contains the data we have (these excel sheets often contain multiple tabs,
          and these other tabs are not relevant to our analysis).
        * Loop through the two directories to load in sheet and, trigger print statements to show that a file did not load in if it did not
          successfully load in. Then concatenates the rows in each loaded sheet to a new larger sheet.
        * Drop duplicates and then filter for rows that include only new displacements
        * Agreggate to per province, per month
        * Merge displacements and returnees data and calculate net IDP flows 
   * Output
     * Returns newly merged data with net monthly IDP flows for Ituri, Nord-kivu, and Sud-kivu provinces as [idp_dat_eastern_drc.csv]([url](https://drive.google.com/file/d/1Icg82SmehaQlIPJnlBBfYQGRKt6Bec6d/view?usp=drive_link))

3. [02_Merging+Regression.ipynb]([url](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/code/02_Merging%2BRegression.ipynb))
   * Packages needed:
     * pandas, numpy, linearmodels, statsmodels
   * Data:
     * [idp_dat_eastern_drc.csv]([url](https://drive.google.com/file/d/1Icg82SmehaQlIPJnlBBfYQGRKt6Bec6d/view?usp=drive_link))
     * [iati-drc-cleaned.csv]([url](https://drive.google.com/file/d/1TZnA1IfYYDwzBSzfgx-7eOlnrBvtRA7Y/view?usp=drive_link))
   * Workflow:
     * Load in data
     * Standardize province names (some discrepancies still existed)
     * For IATI data, Filter IATI to eastern provinces and calculate the monthly spend rate for each aid project
     * Loop through each province-month in IDP data to calculate the number of aid projects that started in the province in the 6 months
       prior to that observation province and all aid projects that were actively running during that observation month
       to capture the baseline level of aid already present in the province. Append this data to a new list called records
     * Merge this new list with the IDP data and log transform the aid spend. Aid spending is highly right-skewed since most of the
       aid dollars are concentrated in a few very large projects while most projects are small, necessitating a log transformation.
     * Run ordinary least squares regression. Dependent variable: net monthly displacement flows per province per month.
       Independent variables: log of new project monthly spend (treatment variable) and log of total active monthly spend (control).
       Province fixed effects, excluded time fixed effects, and used robust standard errors 
   * Output
     * Regression table that was saved as [regression_results.txt]([url](https://github.com/zipcity15/QSS20-S26-Final_Project-Jack_Zipper/blob/main/output/regression_results.txt))


# Challenges
Main challenge: Low statistical power. There are only 57 total rows across the 3 provinces over a little over five years. On average that's a 
new data point every three months, which might not be granular enough.
Other challenge: No statistical siginficance. Initial outputs show the relationship between aid and net IDP flows is not statistically
significant 

