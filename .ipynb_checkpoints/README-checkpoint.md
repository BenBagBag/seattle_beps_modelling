# Models to Predict Emissions between 2027-2050 with BEPS

This repo models emissions from large (>20k sq ft) Seattle buildings between 2027 and 2050 for different benchmark proposals for BEPS.

The original model was built in Excel by RMI. This repo corrects some calculation errors in that model and also allows the user to model a new scenario by writing a single new function and then running the model. See below for instructions.

## Input data

Available in `data/input_data`:

- `energy_emissions.csv`: a table of predicted emissions factors for electric, gas, and steam power in Seattle, year by year until 2050. This was predicted by calculating the rate of decline given by the city and assuming that will remain steady. [source needed]
- `jan_proposal_emissions_targets.csv` and `june_proposal_emissions_targets.csv`: the timeline for when each building type/size must meet specific GHGI targets. These are the city's proposals in January and June of 2023. [sources needed]
- `rmi_building_analysis_with_new_col_names.csv`: RMI's original building data, composed of a list of buildings/emissions from the City of Seattle (not identical to what is found in the public dataset on data.seattle.gov), plus calculations for square footage.
- `Reproducing RMI building data cleaning`: this folder is a Jupyter notebook and CSV's associated with reproducing RMI's analysis of buildings' square footage and usage. We get drastically different numbers when we use this data compared to the `rmi_building_analysis_with_new_col_names` data. We know there's a discrepancy between the data the City makes publicly available vs. what they gave to RMI. There could also be mistakes in this data cleaning/processing. This needs more investigation, which we'll have to do if we want to use the 2019 public City data as our source for building data. [source for city data needed]

## Model

The model is a Python class in `models/baseline_model.py`. The model takes the following parameters:

- emissions_path: file path to table of energy emissions factors for each year
- timeline_path: file path for proposed timeline of emissions reduction
- building_data_path: file path for buildings data
- fine_years: array of years where building owners can be fined for not being compliant
- fine_per_sqft: per square foot fee for non-compliance

The model then calculates:


- city_ghgi_target: The GHGI target, as calculated by the sum of: use type * city's target GHGI for that use type * percent of GFA for that use type, for each of the three given use types (col A). If there is no target for any of the use types, this is NaN. If a building is multi-use, and some of the building's uses have a compliance threshold, but others don't, use the expected GHGI (greenhouse gas emissions intensity) if nothing is changed as the GHGI for the portion of the building that is not subject to BEPS yet.
       - Example: A building is 50% retail and 50% multifamily housing. The target for retail in 2033 is 1.03 and there is no target for multifamily housing. This building would have a GHGI of 4.0 in 2033 if no changes were made to it. We estimate the GHGHI target as (0.5 * 1.03) + (0.5 * 4.0) = 2.515.
       - NB: These numbers will be different than the RMI calculations. The RMI model mistakenly used a GHGI of zero for parts of buildings that are not yet subject to BEPS. So in the example above, RMI's model would list the GHGI target as0.5 * 1.03 + 0.5 * 0 = 0.515, which leaves out half the building. Then the target GHGI would actually go up when the multifamily part of the building became subject to BEPS! This model corrects that error.
- expected_baseline: The expected emissions if nothing is changed about the building, as calculated by the sum of: total use energy for type * energy emissions factor for energy type for the three energy types (col C)
- expected_baseline_ghgi: The expected GHGI if nothing is changed about the building (col B), as calculated by the expected emissions / total GFA
- compliant_ghgi: The expected GHGI if the building is compliant with BEPS, as defined by (col H):
       - if the BEPS GHGI target is lower than the expected GHGI, use the BEPS GHGI target
       - if the expected GHGI is lower than the BEPS GHGI target, use the expected GHGI
- compliant_emissions: The expected emissions if the building is compliant with BEPS, as defined by the compliant GHGI * total GFA (col J)
- compliance_status: Whether or not the building is compliant (col K):
       - yes: the baseline GHGI is lower than the expected compliant GHGI for this year
       - no: the baseline GHGI is higher than the expected compliant GHGI for this year
       - no requirement yet: the building doesn't have a compliance requirement for this year
- compliance_fees: Noncompliance fees. For years where buildings will be taxed for being noncompliant, this is fine_per_sqft * total GFA

The main method is `calculate_baseline_model`, which takes a start and end year and calculates each building's emissions in that time span.

The model also contains methods for breaking down the total emissions for each year once the model has been run (`get_total_emissions_by_year`), as well as a function to calculate the amount emissions have decreased by a given year (`get_percent_emissions_reduction_by_given_year`). 

## Using the model

1. Install the requirements: `$ pip install -r requirements.txt`
2. Start a Jupyter notebook (included in the requirements.txt file): `$ jupyter notebook`
3. This will open a UI in your default browser. You can then explore files and run code. You can go to `Help` -> `User Interface Tour` if you're not familiar with Jupyter notebooks.
4. The models, with their results, are in `models/Jan and June Proposals.ipynb`. 
