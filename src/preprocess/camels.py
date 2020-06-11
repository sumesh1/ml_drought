from pathlib import Path
from .base import BasePreProcessor
import numpy as np
import xarray as xr
import pandas as pd
import geopandas as gpd
from typing import Dict, List, Tuple
import pickle


class CAMELSGBPreprocessor(BasePreProcessor):
    """ Preprocesses the CAMELSGB data """
    dataset = "camels"

    def __init__(self, data_folder: Path = Path("data")):
        super(CAMELSGBPreprocessor, self).__init__(data_folder=data_folder)
        # initialise paths
        base_camels_dir = self.data_folder / "raw/CAMELS_GB_DATASET"
        self.attributes_dir = base_camels_dir / "Catchment_Attributes"
        self.timeseries_dir = base_camels_dir / "Catchment_Timeseries"
        self.shp_path = base_camels_dir / "Catchment_Boundaries/CAMELS_GB_catchment_boundaries.shp"

        assert self.attributes_dir.exists()
        assert self.timeseries_dir.exists()

        # get all filepaths for csv files in CAMELS_GB_DATASET folder
        self.attrs_csvs = [d for d in self.attributes_dir.iterdir() if d.name.endswith('.csv')]
        self.ts_csvs = [d for d in self.timeseries_dir.iterdir()]
        self.gauge_ids = [int(d.name.split('ies_')[-1].split('_')[0]) for d in self.timeseries_dir.iterdir()]

    def preprocess(self) -> None:
        dynamic_ds = self.load_dynamic_data()
        static_ds = self.load_static_data()
        boundaries_gdf = self.load_boundaries_data()

        dynamic_ds.to_netcdf(self.interim / "data.nc")
        static_ds.to_netcdf(self.interim / "static/data.nc")
        pickle.dump(open(self.interim / "boundaries_gdf.pkl", "wb"), boundaries_gdf)

    def _get_coordinates(self) -> Tuple[np.ndarray, List[str]]:
        """get the coordinates for the dataset object from the first csv file

        Returns:
            Tuple[np.ndarray, List[str]]: Array of times and list of dynamic variables
        """
        # load one dummy dataset to get ds coordinates
        dummy_df = pd.read_csv(self.ts_csvs[0])
        times = np.array(dummy_df.date)
        dynamic_vars = [c for c in dummy_df.columns if c != 'date']
        return times, dynamic_vars

    def load_dynamic_data(self) -> xr.Dataset:
        times, dynamic_vars = self._get_coordinates()
        # load all dynamic data into memory
        dfs = [pd.read_csv(d) for d in self.ts_csvs]

        # create dictionary of dynamic data (as a numpy array / matrix)
        dynamic_data_dict = {}
        for variable in dynamic_vars:
            vals = np.array([df[variable].values for df in dfs]).T
            dynamic_data_dict[variable] = vals

        # create the dims/coords for the xarray object
        dims = ["time", "station_id"]
        coords = {"station_id": self.gauge_ids, "time": times}

        dynamic_ds = xr.Dataset(
            {
                variable_name: (dims, dynamic_data_dict[variable_name])
                for variable_name in dynamic_data_dict.keys()
            }, coords=coords
        )

        print("Loaded all dynamic data into `dynamic_ds`")

        # Fix the coordinates
        dynamic_ds["station_id"] = dynamic_ds["station_id"].astype(
            np.dtype("int64")
        )
        dynamic_ds = dynamic_ds.sortby("station_id")

        # ensure that time is datetime64 dtype
        dynamic_ds["time"] = dynamic_ds["time"].astype(np.dtype("datetime64[ns]"))

        return dynamic_ds

    def load_static_data(self) -> xr.Dataset:
        static_groupings = [
            d.name.replace('.csv', '').replace('CAMELS_GB_', '') for d in self.attrs_csvs
        ]

        static_dfs = [pd.read_csv(d) for d in self.attrs_csvs]
        group_dictionary: Dict[str, List[str]] = dict(zip(static_groupings, [list(df.columns) for df in static_dfs]))

        # join into one dataframe
        static_df = pd.concat(static_dfs, axis=1)

        # create xr object
        static_vars = [c for c in static_df.columns if c != 'gauge_id']
        dims = ["station_id"]
        coords = {"station_id": static_df.gauge_id.iloc[:, 0].values}

        static_ds = xr.Dataset(
            {
                variable_name: (dims, static_df[variable_name].values)
                for variable_name in static_vars
            }, coords=coords
        )

        # Fix the coordinates
        static_ds["station_id"] = static_ds["station_id"].astype(
            np.dtype("int64")
        )
        static_ds = static_ds.sortby("station_id")

        return static_ds

    def load_boundaries_data(self) -> gpd.GeoDataFrame:
        """Read the boundaries data to a GeoDataFrame

        Returns:
            gpd.GeoDataFrame: read the
        """
        gdf = gpd.read_file(self.shp_path)
        return gdf


