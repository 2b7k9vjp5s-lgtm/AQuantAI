# ML and Qlib Foundation

Phase 4 creates a guarded ML research foundation. The goal is contract validation and adapter boundaries, not production model training or investment-performance claims.

## Experiment Boundary

`MLExperimentConfig` describes a research experiment with:

- `experiment_name`
- `model_name`
- `universe`
- `feature_columns`
- `label_window`

## Feature Contract

Feature DataFrames must contain:

- `feature_date`
- `stock_code`
- feature columns derived from factors or normalized market data
- `universe`

Feature columns are explicit per experiment so tests and future training runs know exactly what is consumed.

Feature rows are unique by `feature_date`, `stock_code`, and `universe`. Every configured feature value must be finite and numeric, and the baseline checks that all input rows match the experiment universe.

## Label Contract

Label DataFrames must contain:

- `label_date`
- `stock_code`
- `future_return`
- `label_window`
- `universe`

Labels are local contract fixtures in Phase 4. No live data ingestion is added.

## Prediction Output Contract

Prediction results must contain:

- `prediction_date`
- `stock_code`
- `model_name`
- `prediction_score`
- `prediction_rank`
- `universe`

Prediction ranks are deterministic within each prediction date and universe. Equal prediction scores use `stock_code` as the final tie-break.

## Baseline Model

The initial baseline averages selected numeric feature columns and ranks stocks by the resulting score. It exists only to validate interfaces and downstream compatibility. It is not a production model and does not claim predictive performance.

## Qlib Adapter Boundary

Qlib-specific imports are isolated in `ml/qlib/adapter.py`. Core ML modules do not import Qlib. The adapter imports Qlib lazily and can be mocked in tests. Qlib is not forced into runtime dependencies in Phase 4.

## Phase 4 Limitations

Phase 4 does not implement production model training, hyperparameter search, model registry, scheduled retraining, AI Research Agent workflows, dashboard UI, broker APIs, order placement, automatic trading, live market data calls in tests, or claims about investment profitability.
