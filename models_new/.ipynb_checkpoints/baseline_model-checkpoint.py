import pandas as pd
import numpy as np

class BaselineBEPSModel:
    # be sure to remove scenario results option
    def __init__(self, emissions_path, timeline_path, building_data_path, fine_years, fine_per_sqft, scenario_results = None):
        '''
        emissions_path: file path to table of energy emissions factors for each year
        timeline_path: file path for proposed timeline of emissions reduction
        building_data_path: file path for buildings data
        fine_years: array of years where building owners can be fined for not being compliant
        '''
        self.emissions_path = emissions_path
        self.timeline_path = timeline_path
        self.building_data_path = building_data_path
        self.fine_years = fine_years
        self.fine_per_sqft = fine_per_sqft
        self.scenario_results = pd.read_csv(scenario_results)

    # Loading data
    
    def _load_timeline_data(self):
        self.timeline = pd.read_csv(self.timeline_path)

    def _load_building_data(self):
        self.building_data = pd.read_csv(self.building_data_path)

    def _load_emissions_data(self):
        emissions = pd.read_csv(self.emissions_path)
        emissions.set_index('Year', inplace=True)
        self.energy_emissions = emissions

    def _load_input_data(self):
        self._load_timeline_data()
        self._load_building_data()
        self._load_emissions_data()

    # Calculating the baseline model
    
    def _find_ghgi_standard(self, year, building_type, sq_ft_class, alt_timeline = None):
        '''
        Find the GHGI standard in the model's timeline for a given year, building type, and building size.

        alt_timeline: timeline data frame
        '''
        # building types listed as NAN don't count towards the policy, so their emissions and sq ft are calculated as zero
        if pd.isna(building_type) or building_type == 'nan':
            return 0

        timeline = alt_timeline or self.timeline
        row = timeline[(timeline['year'] == year) & (timeline['sq_ft_classification'] == sq_ft_class) & (timeline['building_type'] == building_type)]
        return row.iloc[0]['ghgi'] 
    
    def _get_expected_baseline(self, building, year):
        '''
        Find the expected baseline GHGE for a given year if the building makes no changes
        '''
        electric_emissions = building['Electricity(kBtu)'] * self.energy_emissions.loc[year]['Electricity emission factor (kgCO2e/kBtu)']
        steam_emissions = building['SteamUse(kBtu)'] * self.energy_emissions.loc[year]['Steam emission factor (kgCO2e/kBtu)']
        gas_emissions = building['NaturalGas(kBtu)'] * self.energy_emissions.loc[year]['Gas emission factor (kgCO2e/kBtu)']
        return electric_emissions + steam_emissions + gas_emissions
    
    def _get_expected_baseline_ghgi(self, building):
        '''
        Return the expected GHGI for a bulding if the building makes no changes
        '''
        if building['Total GFA for Policy'] == 0:
            return 0

        return building['expected_baseline'] / building['Total GFA for Policy']
    
    def _fill_in_expected_baselines(self, year_low, year_high, input_df, output_df):
        '''
        input_df: dataframe without any calculations, only building data
        output_df: df with OSE ID, building name, total sq ft, sq ft classification, year, and expected baseline for each year in between year_low and year_high
        '''
        for year in range(year_low, year_high + 1):
            temp_df = input_df[['OSEBuildingID', 'BuildingName', 'Total GFA for Policy', 'sq_ft_classification', 'LargestPropertyUseType OSE', 'SecondLargestPropertyUseType OSE', 'ThirdLargestPropertyUseType OSE']]
            temp_df['year'] = pd.Series([year]*len(temp_df))
            temp_df['expected_baseline'] = input_df.apply(lambda building: self._get_expected_baseline(building, year), axis=1)

            output_df = pd.concat([output_df, temp_df])


        return output_df
    
    def _get_city_ghgi(self, building, alt_timeline = None):
        '''
        alt_timeline: dataframe of alternative target timeline
        '''
        year = building['year']
        baseline_ghgi = building['expected_baseline_ghgi']
        orig_building_row = self.building_data[self.building_data['OSEBuildingID'] == building['OSEBuildingID']].iloc[0]

        first_use_ghgi = self._find_ghgi_standard(year, orig_building_row['LargestPropertyUseType OSE'], building['sq_ft_classification'], alt_timeline)
        second_use_ghgi = self._find_ghgi_standard(year, orig_building_row['SecondLargestPropertyUseType OSE'], building['sq_ft_classification'], alt_timeline)
        third_use_ghgi = self._find_ghgi_standard(year, orig_building_row['ThirdLargestPropertyUseType OSE'], building['sq_ft_classification'], alt_timeline)

        return (orig_building_row['LargestPropertyUseType Percent GFA'] * (baseline_ghgi if pd.isna(first_use_ghgi) else first_use_ghgi)) + (orig_building_row['SecondLargestPropertyUseType Percent GFA'] * (baseline_ghgi if pd.isna(second_use_ghgi) else second_use_ghgi)) + (orig_building_row['ThirdLargestPropertyUseType Percent GFA'] * (baseline_ghgi if pd.isna(third_use_ghgi) else third_use_ghgi))

    def _get_compliant_ghgi(self, building):
        '''
        Return the lower of: the city's benchmark and the expected emissions for a building
        '''
        return min(building['expected_baseline_ghgi'], building['city_ghgi_target'])

    def _get_compliant_emissions(self, building):
        return building['compliant_ghgi'] * building['Total GFA for Policy']

    def _get_compliance_status(self, building):
        year = building['year']
        sqft_class = building['sq_ft_classification']
        if pd.isna(self._find_ghgi_standard(year, building['LargestPropertyUseType OSE'], sqft_class)) and pd.isna(self._find_ghgi_standard(year, building['SecondLargestPropertyUseType OSE'], sqft_class)) and pd.isna(self._find_ghgi_standard(year, building['ThirdLargestPropertyUseType OSE'], sqft_class)): 
            return 'Not due yet'
        elif building['expected_baseline_ghgi'] < building['city_ghgi_target']:
            return 'Yes'
        else:
            return 'No'
        
    def _get_noncompliance_fines(self, building):
        if building['year'] in self.fine_years:
            return building['Total GFA for Policy'] * self.fine_per_sqft
        else:
            return 0

    def _calculate_baseline_model_without_saving(self, start_year, end_year, alternate_timeline):
        self._load_input_data()

        if alternate_timeline:
            alt_timeline = pd.read_csv(alternate_timeline)
        
        baseline_building_info = pd.DataFrame(columns=['OSEBuildingID', 'BuildingName', 'Total GFA for Policy', 'sq_ft_classification'])
        scen_calcs = self._fill_in_expected_baselines(start_year, end_year, self.building_data, baseline_building_info)
        
        scen_calcs['expected_baseline_ghgi'] = scen_calcs.apply(lambda building: self._get_expected_baseline_ghgi(building), axis=1)
        scen_calcs['city_ghgi_target'] = scen_calcs.apply(lambda building: self._get_city_ghgi(building, alt_timeline), axis=1)
        scen_calcs['compliant_ghgi'] = scen_calcs.apply(lambda building: self._get_compliant_ghgi(building), axis=1)
        scen_calcs['compliant_emissions'] = scen_calcs.apply(lambda building: self._get_compliant_emissions(building), axis=1)
        scen_calcs['compliance_status'] = scen_calcs.apply(lambda building: self._get_compliance_status(building), axis=1)
        scen_calcs['compliance_fees'] = scen_calcs.apply(lambda building: self._get_noncompliance_fines(building), axis=1)

        return scen_calcs
    
    def calculate_baseline_model(self, start_year, end_year, alternate_timeline = None):
        '''
            start_year: year to begin calculations (inclusive)
            end_year: year to end calculations (inclusive)
            alternate_timeline: file path to an alternative timeline. Defaults to None
        '''
        scen_calcs = self._calculate_baseline_model_without_saving(self, start_year, end_year, alternate_timeline)
        self.scenario_results = scen_calcs

        print('Model calculations complete. Access the model dataframe as model_name.scenario_results')

    # Calculating statistics about the model
    
    def get_total_emissions_by_year(self):
        if self.scenario_results is None:
            print('You need to run the calculate_baseline_model method before getting the emissions by year')
            return
        
        grouped = self.scenario_results[self.scenario_results['sq_ft_classification'] != 'F'].groupby('year')['compliant_emissions'].sum()
        grouped = grouped.to_frame()

        self.emissions_by_year = grouped
        print('Emissions by year calculations complete. Access the annual emissions dataframe as model_name.emissions_by_year')

    def get_percent_emissions_reduction_by_given_year(self, year):
        # 2026 emissions are the same as the 2027 baseline
        baseline_2026 = self.scenario_results[self.scenario_results['year'] == 2027]['expected_baseline'].sum()

        emissions_in_target_year = self.scenario_results[self.scenario_results['year'] == year]['compliant_emissions'].sum()

        return 1 - (emissions_in_target_year / baseline_2026)

    # Calculating how much to reduce targets in order to hit X% reduction in emissions
    
    def create_temp_emissions_timeline_file(percent):
        # method to create temporary file for emissions
        # percent is % of original baseline, not percent reduction of original baseline
        
        temp_timeline = self.timeline['ghgi'] * (percent / 100.0)
        file_name = f'tmp/timeline_{percent}_percent_of_policy.csv'
        temp_timeline.to_csv(file_name)
        return temp_timeline, file_name

    def find_reduction_percent(self, target_kg, target_year, file_path = None):
        # Basic BST algorithm to find target reduction needed to hit a particular goal
        
        # make temporary directory for timeline files
        os.mkdir('tmp')
    
        min_emissions = target_kg - 5000
        max_emissions = target_kg + 5000
    
        high = 100
        low = 0
        found_target = False
    
        while not found_target:
            percent_of_orig_emissions = (high + low) / 2
            reduced_timeline, reduced_timeline_path = create_temp_emissions_timeline_file(percent_of_orig_emissions, timeline_path)

            model = this._calculate_baseline_model_without_saving(target_year, target_year, reduced_timeline)
            emissions_in_target_year = model['compliant_emissions'].sum()
    
            if min_emissions < emissions_in_target_year < max_emissions:
                print(f'You can achieve {target_kg} kg/yr in {target_year} by reducing the baselines by {100 - percent_of_orig_emissions}%.')
                # move file
                os.rename(reduced_timeline_path, reduced_timeline_path.replace('tmp/', file_path))
    
                # delete tmp directory
                shutil.rmtree('tmp')
    
                found_target = True
    
            else:
                if emissions_in_2040 < target_kg:
                    low = percent_of_orig_emissions
                else:
                    high = percent_of_orig_emissions