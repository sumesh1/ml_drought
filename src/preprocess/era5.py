from pathlib import Path
from functools import partial
import xarray as xr
import multiprocessing
from shutil import rmtree

from typing import Optional

from .base import _BasePreProcessor


class ERA5MonthlyMeanPreprocessor(_BasePreProcessor):
    """Preprocesses ERA5 Monthly data

    :param data_folder: The location of the data folder
    """

    dataset = 'reanalysis-era5-single-levels-monthly-means'

    @staticmethod
    def _create_filename(netcdf_filepath: Path,
                         subset_name: Optional[str] = None) -> str:

        var_name = netcdf_filepath.parts[-3]
        months = netcdf_filepath.parts[-1][:-3]
        year = netcdf_filepath.parts[-2]

        stem = f'{year}_{months}_{var_name}'
        if subset_name is not None:
            stem = f'{stem}_{subset_name}'
        return f'{stem}.nc'

    def _preprocess_single(self, netcdf_filepath: Path,
                           subset_str: Optional[str] = 'kenya',
                           regrid: Optional[xr.Dataset] = None) -> None:

        print(f'Processing {netcdf_filepath.name}')
        # 1. read in the dataset
        ds = xr.open_dataset(netcdf_filepath).rename({'longitude': 'lon', 'latitude': 'lat'})

        # 2. chop out EastAfrica
        if subset_str is not None:
            ds = self.chop_roi(ds, subset_str, inverse_lat=True)

        if regrid is not None:
            ds = self.regrid(ds, regrid)

        filename = self._create_filename(
            netcdf_filepath,
            subset_name=subset_str if subset_str is not None else None
        )
        print(f'Saving to {self.interim}/{filename}')
        ds.to_netcdf(self.interim / filename)

        print(f'Done for ERA5 {netcdf_filepath.name}')

    def preprocess(self, subset_str: Optional[str] = 'kenya',
                   regrid: Optional[Path] = None,
                   resample_time: Optional[str] = 'M',
                   upsampling: bool = False,
                   parallel: bool = False,
                   cleanup: bool = True) -> None:
        """ Preprocess all of the ERA5 files to produce
        one subset file.

        :param subset_str: Whether to subset an area when preprocessing. Must be
            one of `{'kenya', 'east_africa', 'ethiopia'}`
        :param regrid: If a Path is passed, the CHIRPS files will be regridded to have
            the same grid as the dataset at that Path. If None, no regridding happens
        :param resample_time: If not None, defines the time length to which the data will
            be resampled
        :param upsampling: If `True`, tells the class the time-sampling will be upsampling.
            In this case, nearest instead of mean is used for the resampling
        :param parallel: If `True`, run the preprocessing in parallel
        :param cleanup: If `True`, delete interim files created by the class
        """
        print(f'Reading data from {self.raw_folder}. Writing to {self.interim}')

        # get the filepaths for all of the downloaded data
        nc_files = self.get_filepaths()

        if regrid is not None:
            regrid = self.load_reference_grid(regrid)

        if parallel:
            pool = multiprocessing.Pool(processes=100)
            outputs = pool.map(partial(self._preprocess_single, subset_str=subset_str,
                                       regrid=regrid), nc_files)
            print("\nOutputs (errors):\n\t", outputs)
        else:
            for file in nc_files:
                self._preprocess_single(file, subset_str, regrid)

        # merge all of the timesteps
        self.merge_files(subset_str, resample_time, upsampling)

        if cleanup:
            rmtree(self.interim)
