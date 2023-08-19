import os
import shutil

from baseline_model import BaselineBEPSModel


# NB: this file is not currently used in the repo

# method to create temporary file for emissions
# percent is % of original baseline, not percent reduction of original baseline
def create_temp_emissions_timeline_file(percent, timeline_path):
    timeline = pd.read_csv(timeline_path)
    timeline['ghgi'] = timeline['ghgi'] * (percent/100.0)
    file_name = f'tmp/timeline_{percent}_percent_of_policy.csv'
    timeline.to_csv(file_name)
    return file_name

def find_reduction_percent(target_kg, target_year, timeline_path, emissions_path, building_data_path, fine_years, fine_per_sqft):
    # make temporary directory for timeline files
    os.mkdir('tmp')

    min_emissions = target_kg - 5000
    max_emissions = target_kg + 5000

    high = 100
    low = 0
    found_target = False

    while not found_target:
        percent_of_orig_emissions = (high + low) / 2
        reduced_timeline_path = create_temp_emissions_timeline_file(percent_of_orig_emissions, timeline_path)

        model = BaselineBEPSModel(emissions_path, reduced_timeline_path, building_data_path, fine_years, fine_per_sqft)
        model.calculate_baseline_model(target_year, target_year)
        emissions_in_2040 = model.scenario_results['compliant_emissions'].sum()

        if min_emissions < emissions_in_2040 < max_emissions:
            print(f'You can achieve {target_kg} kg/yr in {target_year} by reducing the baselines by {100 - percent_of_orig_emissions}%.')
            # move file
            os.rename(reduced_timeline_path, reduced_timeline_path.replace('tmp/', ''))
                      
            # turn model into csv
            model.scenario_results.to_csv(f'emissions_{target_year}_{percent_of_orig_emissions}_of_policy.csv')

            # delete tmp directory
            shutil.rmtree('tmp')

            found_target = True

        else:
            if emissions_in_2040 < target_kg:
                low = percent_of_orig_emissions
            else:
                high = percent_of_orig_emissions