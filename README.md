# Models to Predict Emissions between 2027-2050 with BEPS

This repo models emissions from large (>20k sq ft) Seattle buildings between 2027 and 2050 for different benchmark proposals for BEPS.

The original model was built in Excel by RMI. This repo corrects some calculation errors in that model and also allows the user to model a new scenario by writing a single new function and then running the model. See below for instructions.

## Input data

Available in `data/input_data`:

- `energy_emissions.csv`: a table of predicted emissions factors for electric, gas, and steam power in Seattle, year by year until 2050. This was predicted by calculating the rate of decline given by the city and assuming that will remain steady.
- `jan_proposal_emissions_targets.csv` and `june_proposal_emissions_targets.csv`: the timeline for when each building type/size must meet specific GHGI targets. These are the city's proposals in January and June of 2023.
- `Data cleaning`: this folder is a Jupyter notebook and CSV's associated calculating buildings' square footage and usage.

## Models

There are two models included in this repo:

### The Baseline Model

Found in `models/baseline_model.py`. This class models expected emissions for each building subject to the policy between 2027 and 2050. The model is used in `models/Jan and June Proposals with Baseline Model.ipynb` to calculate emissions under the City's two proposed timelines. The Jupyter notebook also includes a description of the methodology.

### The Alternative Compliance Model

Found in `models/alternative_compliance_model.py`. This class models expected emissions for each building subject to the policy, taking into account a proposed ammendment that will loosen emissions standards for campuses, highly-polluting buildings, and buildings with unclassified use types. The model includes a description of the ammendment.

## Using the model

1. Install the requirements: `$ pip install -r requirements.txt`
2. Start a Jupyter notebook (included in the requirements.txt file): `$ jupyter notebook`
3. This will open a UI in your default browser. You can then explore files and run code. You can go to `Help` -> `User Interface Tour` if you're not familiar with Jupyter notebooks.
4. The Baseline Model, with its results, are in `models/Jan and June Proposals.ipynb`. 
