# Model for a proposal with exceptions for campuses, highly polluting buildings, and unclassified buildings

############################################################################
# NB: Under construction and not fully tested, use at your own discretion. #
############################################################################

# In this proposed ammendment, buildings can use the alternate compliance for all compliance periods if the building is:

# - A building portfolio, district campus, or connected buildings
# - NB: We do not have data to let us determine reliably if a building is part of a portfolio or connected buildings
# - A nonresidential building with more than 50% of the covered building with the building activity type of “Other” or of a type not covered by legislation's building use types
# - A covered building that has a baseline GHGI greater than 3.5 times the covered building’s standard GHGIT for the 2031-2035 compliance interval.
# NB: this model assumes this is the city standard GHGIT for that building in 2035.

# Alternative GHGITs are defined as:

# For nonresidential buildings:

# 75% of the baseline GHGI for the 2027-2030 compliance interval
# 50% of the baseline GHGI for the 2031-2035 compliance interval
# 25% of the baseline GHGI for the 2036-2040 compliance interval
# Net zero for the 2041-2045 compliance interval


# For multifamily residential buildings:

# 75% of the baseline GHGI for the 2031-2035 compliance interval
# 50% of the baseline GHGI for the 2036-2040 compliance interval
# 25% of the baseline GHGI for the 2041-2045 compliance interval
# Net zero for the 2046-2050 compliance interval

import pandas as pd
import numpy as np

from baseline_model import BaselineBEPSModel

class AlternativeComplianceModel(BaselineBEPSModel):
    def __init__(self, emissions_path, timeline_path, building_data_path, fine_years, fine_per_sqft):
        BaselineBEPSModel.__init__(self, emissions_path, timeline_path, building_data_path, fine_years, fine_per_sqft)
        BaselineBEPSModel._load_input_data()
        BaselineBEPSModel._clean_data()

    def _eligible_for_exception_1(building_type):
        '''
            Determine if a building is eligible to use alternative compliance because it is part of a campus or building portfolio.
        '''
        
        # is campus
        if building_type == 'Campus':
            return True

        # TODO: is part of a portfolio
        # We don't have comprehensive data to assess this, so we're skipping for now

        # Connected buildings: we assume these are included in portfolios
        
        return False

    def _eligible_for_exception_2(building, building_type):
        '''
            Determine if a building is eligible to use alternative compliance because >50% of its square footage has a use type not covered by the legislation.
        '''
        if building_type != 'NonResidential':
            return False

        # index of the largest use type that is NaN (no builidng type given in the dataset, presumed to be 'Other')
        is_nan = list(building[['LargestPropertyUseType OSE', 'SecondLargestPropertyUseType OSE', 'ThirdLargestPropertyUseType OSE']]).index(np.nan) if np.nan in list(building[['LargestPropertyUseType OSE', 'SecondLargestPropertyUseType OSE', 'ThirdLargestPropertyUseType OSE']]) else -1

        # index of the largest use type that is 'Other' (distinct from NaN)
        is_other = list(building[['LargestPropertyUseType OSE', 'SecondLargestPropertyUseType OSE', 'ThirdLargestPropertyUseType OSE']]).index('Other') if 'Other' in list(building[['LargestPropertyUseType OSE', 'SecondLargestPropertyUseType OSE', 'ThirdLargestPropertyUseType OSE']]) else -1
        
        gfa_cols = ['percent_sqft_1st', 'percent_sqft_2nd', 'percent_sqft_3rd']
        building_data_row = building_data[building_data['OSEBuildingID'] == building['OSEBuildingID']].iloc[0]
        
        if is_nan > -1 and (building_data_row[gfa_cols[is_nan]] > .5 or building_data_row[gfa_cols[is_other]] > .5):
            return True
        
        return False

    def _get_stand_benchmark_2035(building, baseline):
        '''
            Get the City's standard benchmark GHGI for a specific building.
        '''
        benchmarks_2035 = self.timeline.loc['2031-2035']
        building_data_row = self.building_data[self.building_data['OSEBuildingID'] == building['OSEBuildingID']].iloc[0]
        
        if building['LargestPropertyUseType OSE'] == 'nan' or pd.isna(building['LargestPropertyUseType OSE']):
            largest_ghgit = building_data_row['percent_sqft_1st'] * baseline
        else:
            largest_ghgit = building_data_row['percent_sqft_1st'] * benchmarks_2035[building['LargestPropertyUseType OSE']]
            
        if building['SecondLargestPropertyUseType OSE'] == 'nan' or pd.isna(building['SecondLargestPropertyUseType OSE']):
            second_ghgit = building_data_row['percent_sqft_2nd'] * baseline
        else:
            second_ghgit = building_data_row['percent_sqft_2nd'] * benchmarks_2035[building['SecondLargestPropertyUseType OSE']]
        
        if building['ThirdLargestPropertyUseType OSE'] == 'nan' or pd.isna(building['ThirdLargestPropertyUseType OSE']):
            third_ghgit = building_data_row['percent_sqft_3rd'] * baseline
        else:
            third_ghgit = building_data_row['percent_sqft_3rd'] * benchmarks_2035[building['ThirdLargestPropertyUseType OSE']]
        
        return largest_ghgit + second_ghgit + third_ghgit
        
    def _eligible_for_exception_3(building):
        '''
            Determine if a building is elibigle to use alternative compliance because it is a covered building that has a baseline GHGI greater than 3.5 times the covered building’s standard GHGIT for the 2031-2035 compliance interval
        '''
    
        building_data_row = self.building_data[self.building_data['OSEBuildingID'] == building['OSEBuildingID']].iloc[0]
        baseline_2035 = self.scenario_results[(self.scenario_results['year'] == 2035) & (self.scenario_results['OSEBuildingID'] == building['OSEBuildingID'])].iloc[0]['expected_baseline_ghgi']
        
        ghgit_2035 = self._get_stand_benchmark_2035(building, building_data, baseline_2035)
        baseline_ghgi = self.scenario_results[(self.scenario_results['year'] == 2027) & (self.scenario_results['OSEBuildingID'] == building['OSEBuildingID'])].iloc[0]['expected_baseline_ghgi']
        
        return baseline_ghgi > ghgit_2035 * 3.5

    def _can_use_alternative_ghgit(building):
        building_type = self.building_data[self.building_data['OSEBuildingID'] == building['OSEBuildingID']].iloc[0]['Type_of_Bulding']

        if self._eligible_for_exception_1(building_type):
            return True
        
        if self._eligible_for_exception_2(building, building_type):
            return True
        
        if self._eligible_for_exception_3(building):
            return True
        
        return False

    def _calc_alt_ghgi(building):
        '''
            Calculate expected emissions for a building in a given year under the alternative compliance policy.
            Buildings not eligible for alternative GHGI return NA.

            Input:
                building: a row of data for a specific building in a specific year
        '''
        if not building['can_use_alternative_ghgi']:
            return pd.NA
        
        baseline_ghgi = self.scenario_results[(self.scenario_results['year'] == 2027) & (self.scenario_results['OSEBuildingID'] == building['OSEBuildingID'])].iloc[0]['expected_baseline_ghgi']
        year = building['year']
        
        if self.building_data[self.building_data['OSEBuildingID'] == building['OSEBuildingID']].iloc[0]['Type_of_Bulding'] == 'Multifamily':
            if year < 2031:
                return baseline_ghgi
            if year >= 2031 and year <= 2035:
                return 0.66 * baseline_ghgi
            if year >= 2036 and year <= 2040:
                return 0.33 * baseline_ghgi
            if year > 2041 :
                return 0
        else:
            if year >= 2027 and year <= 2030:
                return baseline_ghgi
            if year >= 2031 and year <= 2035:
                return 0.75 * baseline_ghgi
            if year >= 2036 and year <= 2040:
                return 0.5 * baseline_ghgi
            if year >= 2041 and year <= 2045:
                return .25 * baseline_ghgi
            if year > 2045:
                return 0

    def _choose_compliance(building):
        '''
            Determine the expected GHGI for a given building in a given year. 
            Buildings eligible for alternative GHGI return the largest allowed GHGI for that building.
            Buildings not eligible for alternative GHGI will return the regular compliant_ghgi.

            Input: building: a row of data for a specific building in a specific year
        '''
        if pd.isna(building['alt_ghgi']):
            return building['compliant_ghgi']
        else:
            return max(building['compliant_ghgi'], building['alt_ghgi'])

    def _calc_alt_emissions(building):
        return building['alt_compliance'] * building['Total GFA for Policy']
    
    def calculate_alternative_compliance_model():
        scen_calcs = BaselineBEPSModel._calculate_baseline_model_without_saving(start_year, end_year)
        self.scenario_results = scen_calcs

        self.building_data['can_use_alternative_compliance'] = self.building_data.apply(lambda building: self.can_use_alternative_ghgit(building), axis=1)

        self.scenario_results['alternative_ghgi'] = self.scenario_results.apply(lambda building: self._calc_alt_ghgi(building), axis=1)
        self.scenario_results['alternative_compliant_ghgi'] = self.scenario_results.apply(lambda building: self._choose_compliance(building), axis=1)
        # This is the expected emissions under the alternative compliance option
        # For buildings not eligible for alternative GHGI, this will be the same as compliant_ghgi
        self.scenario_results['alternative_compliant_emissions'] = self.scenario_results.apply(lambda building: self._calc_alt_emissions(building), axis=1)
        