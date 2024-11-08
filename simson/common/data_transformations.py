from copy import copy
import numpy as np

from sodym import (
    StockArray, DynamicStockModel, FlowDrivenStock,
    DimensionSet, NamedDimArray, Process, Parameter
)

from .data_extrapolations import SigmoidalExtrapolation, ExponentialExtrapolation, WeightedProportionalExtrapolation


def extrapolate_stock(
        historic_stocks: StockArray, dims: DimensionSet,
        parameters: dict[str, Parameter], curve_strategy: str
        ):
    """Performs the per-capita transformation and the extrapolation."""

    # transform to per capita
    pop = parameters['population']
    historic_pop       = NamedDimArray.from_dims_superset(dims_superset=dims, dim_letters=('h','r'))
    historic_gdppc     = NamedDimArray.from_dims_superset(dims_superset=dims, dim_letters=('h','r'))
    historic_stocks_pc = NamedDimArray.from_dims_superset(dims_superset=dims, dim_letters=('h','r','g'))
    stocks_pc          = NamedDimArray.from_dims_superset(dims_superset=dims, dim_letters=('t','r','g'))
    stocks             = NamedDimArray.from_dims_superset(dims_superset=dims, dim_letters=('t','r','g'))

    historic_pop[...] = pop[{'t': dims['h']}]
    historic_gdppc[...] = parameters['gdppc'][{'t': dims['h']}]
    historic_stocks_pc[...] = historic_stocks / historic_pop

    if curve_strategy == "GDP_regression":
        gdp_regression(historic_stocks_pc.values, parameters['gdppc'].values, stocks_pc.values)
    elif curve_strategy == 'Exponential_GDP_regression':
        gdp_regression(historic_stocks_pc.values, parameters['gdppc'].values, stocks_pc.values,
                       fitting_function_type='exponential')
    else:
        raise RuntimeError(f"Extrapolation strategy {curve_strategy} is not defined. "
                           f"It needs to be 'GDP_regression'.")

    # transform back to total stocks
    stocks[...] = stocks_pc * pop

    #visualize_stock(self, self.parameters['gdppc'], historic_gdppc, stocks, historic_stocks, stocks_pc, historic_stocks_pc)
    return StockArray(**dict(stocks))


def extrapolate_to_future(historic_values : NamedDimArray, scale_by : NamedDimArray) -> NamedDimArray:

    if not historic_values.dims.letters[0] == 'h':
        raise ValueError("First dimension of historic_parameter must be historic time.")
    if not scale_by.dims.letters[0] == 't':
        raise ValueError("First dimension of scaler must be time.")
    if not set(scale_by.dims.letters[1:]).issubset(historic_values.dims.letters[1:]):
        raise ValueError("Scaler dimensions must be subset of historic_parameter dimensions.")

    all_dims = historic_values.dims.union_with(scale_by.dims)

    dim_letters_out = ('t',) + historic_values.dims.letters[1:]
    extrapolated_values = NamedDimArray.from_dims_superset(dims_superset=all_dims, dim_letters=dim_letters_out)

    scale_by = scale_by.cast_to(extrapolated_values.dims)

    extrapolation = WeightedProportionalExtrapolation(
        data_to_extrapolate=historic_values.values,
        target_range=scale_by.values)
    extrapolated_values.set_values(extrapolation.extrapolate())

    return extrapolated_values


def gdp_regression(historic_stocks_pc, gdppc, prediction_out, fitting_function_type='sigmoid'):
    shape_out = prediction_out.shape
    assert len(shape_out) == 3, "Prediction array must have 3 dimensions: Time, Region, Good"
    pure_prediction = np.zeros_like(prediction_out)
    n_historic = historic_stocks_pc.shape[0]

    if fitting_function_type == 'sigmoid':
        extrapolation_class = SigmoidalExtrapolation
    elif fitting_function_type == 'exponential':
        extrapolation_class = ExponentialExtrapolation
    else:
        raise ValueError('fitting_function_type must be either "sigmoid" or "exponential".')

    for i_region in range(shape_out[1]):
        for i_good in range(shape_out[2]):
            region_category_historic_stock = historic_stocks_pc[:, i_region, i_good]
            regional_gdppc = gdppc[:, i_region]
            extrapolation = extrapolation_class(
                data_to_extrapolate=region_category_historic_stock,
                target_range=regional_gdppc
            )
            pure_prediction[:, i_region, i_good] = extrapolation.regress()

    prediction_out[...] = pure_prediction - (
        pure_prediction[n_historic - 1, :, :] - historic_stocks_pc[n_historic - 1, :, :]
        )
    prediction_out[:n_historic,:,:] = historic_stocks_pc


def prepare_stock_for_mfa(
        dims: DimensionSet, dsm: DynamicStockModel, prm: dict[str, Parameter], use: Process
    ):
    # We use an auxiliary stock for the prediction step to save dimensions and computation time
    # Therefore, we have to transfer the result to the higher-dimensional stock in the MFA system
    stock_extd = dsm.stock * prm['material_shares_in_goods'] * prm['carbon_content_materials']
    inflow = dsm.inflow * prm['material_shares_in_goods'] * prm['carbon_content_materials']
    outflow = dsm.outflow * prm['material_shares_in_goods'] * prm['carbon_content_materials']
    stock_dims = dims.get_subset(('t','r','g','m','e'))
    stock_extd = StockArray(values=stock_extd.values, name='in_use_stock', dims=stock_dims)
    inflow = StockArray(values=inflow.values, name='in_use_inflow', dims=stock_dims)
    outflow = StockArray(values=outflow.values, name='in_use_outflow', dims=stock_dims)
    stock = FlowDrivenStock(
        stock=stock_extd, inflow=inflow, outflow=outflow, name='in_use', process_name='use',
        process=use,
    )
    return stock
