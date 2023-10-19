import numpy as np
from src.tools.tools import get_np_from_df
from src.tools.config import cfg
from src.read_data.load_data import load_stocks


def _calc_trade_factor(df_add, df_sub, df_div):
    df_trade = df_add.sub(df_sub, fill_value=0)
    df_trade_factor = df_trade.div(df_div, fill_value=1)
    np_trade_factor = get_np_from_df(df_trade_factor, data_split_into_categories=False)
    return np_trade_factor


def calc_change_timeline(factor, base_year, get_timeline_from_baseyear=False):
    n_years = cfg.end_year - base_year + 1
    base_year_timeline = np.linspace(1, factor, n_years)

    if get_timeline_from_baseyear:
        return base_year_timeline

    timeline = np.zeros([cfg.n_years] + list(factor.shape)[:])
    timeline[base_year - cfg.start_year:, :] = base_year_timeline
    return timeline


def get_dsm_data(dsms):
    stocks = np.array([[[dsm_scenario.s for dsm_scenario in dsms_category] for dsms_category in dsms_region]
                       for dsms_region in dsms])
    inflows = np.array([[[dsm_scenario.i for dsm_scenario in dsms_category] for dsms_category in dsms_region]
                        for dsms_region in dsms])
    outflows = np.array([[[dsm_scenario.o for dsm_scenario in dsms_category] for dsms_category in dsms_region]
                         for dsms_region in dsms])
    stocks = np.moveaxis(stocks, -1, 0)
    inflows = np.moveaxis(inflows, -1, 0)
    outflows = np.moveaxis(outflows, -1, 0)

    return stocks, inflows, outflows


def get_stock_data_country_specific_areas(country_specific):
    df_stocks = load_stocks(country_specific=country_specific, per_capita=True)
    areas = list(df_stocks.index.unique(level=0))

    return areas


if __name__ == '__main__':
    print('test')
