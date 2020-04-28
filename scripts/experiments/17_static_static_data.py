import sys

sys.path.append("../..")

from scripts.utils import _rename_directory, get_data_path
from _base_models import regression, linear_nn, rnn, earnn, persistence, climatology
from src.engineer import Engineer


def engineer(pred_months=3, target_var="boku_VCI", process_static=False):
    engineer = Engineer(
        get_data_path(), experiment="one_month_forecast", process_static=process_static
    )
    engineer.engineer(
        test_year=[y for y in range(2016, 2019)],
        target_variable=target_var,
        pred_months=pred_months,
        expected_length=pred_months,
    )


if __name__ == "__main__":
    # 1. Run the engineer
    target_var = "boku_VCI"
    pred_months = 3
    # engineer(
    #     pred_months=pred_months,
    #     target_var=target_var,
    #     process_static=True
    # )

    # NOTE: why have we downloaded 2 variables for ERA5 evaporaton
    # important_vars = ["VCI", "precip", "t2m", "pev", "p0005", "SMsurf", "SMroot"]
    # always_ignore_vars = ["ndvi", "p84.162", "sp", "tp", "Eb", "E", "p0001"]
    important_vars = ["boku_VCI", "precip", "t2m", "pev", "E", "SMsurf"]
    always_ignore_vars = [
        "VCI",
        "p84.162",
        "sp",
        "tp",
        "Eb",
        "VCI1M",
        "RFE1M",
        "VCI3M",
        "modis_ndvi",
        "SMroot",
        "lc_class",
        "no_data_one_hot",
    ]  # "ndvi",

    # -------------
    # baseline models
    # -------------
    # persistence()
    # climatology()

    # regression(
    #     ignore_vars=always_ignore_vars,
    #     experiment="one_month_forecast",
    #     include_pred_month=True,
    #     surrounding_pixels=None,
    #     explain=False,
    # )

    # # gbdt(ignore_vars=always_ignore_vars)
    # linear_nn(
    #     ignore_vars=always_ignore_vars,
    #     experiment="one_month_forecast",
    #     include_pred_month=True,
    #     surrounding_pixels=None,
    #     explain=False,
    #     num_epochs=50,
    #     early_stopping=5,
    #     layer_sizes=[256],
    #     include_latlons=True,
    #     include_yearly_aggs=False,
    #     clear_nans=True,
    # )

    # -------------
    # LSTM
    # -------------
    rnn(
        experiment="one_month_forecast",
        include_pred_month=True,
        surrounding_pixels=None,
        explain=False,
        static="features",
        ignore_vars=always_ignore_vars,
        num_epochs=50,
        early_stopping=5,
        hidden_size=256,
        include_latlons=True,
        include_yearly_aggs=False,
        clear_nans=True,
    )

    # -------------
    # EALSTM
    # -------------
    earnn(
        experiment="one_month_forecast",
        include_pred_month=True,
        surrounding_pixels=None,
        pretrained=False,
        explain=False,
        static="features",
        ignore_vars=always_ignore_vars,
        num_epochs=50,
        early_stopping=5,
        hidden_size=256,
        static_embedding_size=64,
        include_latlons=True,
        include_yearly_aggs=False,
        clear_nans=True,
    )

    # rename the output file
    data_path = get_data_path()

    _rename_directory(
        from_path=data_path / "models" / "one_month_forecast",
        to_path=data_path / "models" / "one_month_forecast_BASE_static_vars",
        with_datetime=True,
    )
