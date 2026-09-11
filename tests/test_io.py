import math
import re

import numpy as np
import pandas as pd
import pytest

from geofig_engine.io import (
    haversine, path_distance, gen_markers, gen_markers_series, Pipeline, PipelineStep,
    equisflat_to_sample_df, sample_df_to_equisflat, equis_crosstab_to_flat,
    equisflat_normalize_units, SI_PREFIXES,
    ecesis_to_sample_df, create_bins,
)
from geofig_engine.io.markers import gen_markers_cross_grouping, DEFAULT_MARKERS, DEFAULT_PALETTE


class TestHaversine:
    def test_known_distance(self):
        d = haversine(0, 0, 0, 1)
        assert abs(d - 111.195) < 0.1

    def test_same_point_returns_zero(self):
        d = haversine(-73.9, 40.7, -73.9, 40.7)
        assert abs(d) < 1e-6

    def test_antipodal(self):
        d = haversine(0, 0, 180, 0)
        assert abs(d - 20015) < 10

    def test_series_input(self):
        lon = pd.Series([0.0, 0.0])
        lat = pd.Series([0.0, 1.0])
        d = haversine(lon.iloc[0], lat.iloc[0], lon.iloc[1], lat.iloc[1])
        assert abs(d - 111.195) < 0.1


class TestPathDistance:
    def test_single_point_zero(self):
        d = path_distance(pd.Series([0.0]), pd.Series([0.0]))
        assert d.iloc[0] == 0.0

    def test_two_points(self):
        d = path_distance(pd.Series([0.0, 0.0]), pd.Series([0.0, 1.0]))
        assert abs(d.iloc[1] - 111.195) < 0.1
        assert d.iloc[0] == 0.0

    def test_cumulative_false(self):
        d = path_distance(pd.Series([0.0, 0.0, 0.0]), pd.Series([0.0, 1.0, 2.0]), cumulative=False)
        assert abs(d.iloc[1] - 111.195) < 0.1
        assert abs(d.iloc[2] - 111.195) < 0.1
        assert d.iloc[0] == 0.0

    def test_cumulative_true(self):
        d = path_distance(pd.Series([0.0, 0.0, 0.0]), pd.Series([0.0, 1.0, 2.0]), cumulative=True)
        assert abs(d.iloc[2] - 2 * 111.195) < 0.2
        assert d.iloc[0] == 0.0


class TestGenMarkers:
    def test_returns_dict(self):
        result = gen_markers(["A", "B", "C"])
        assert isinstance(result, dict)
        assert set(result.keys()) == {"A", "B", "C"}

    def test_each_entry_has_marker_and_color(self):
        result = gen_markers(["A", "B"])
        for v in ("A", "B"):
            assert "marker" in result[v]
            assert "color" in result[v]

    def test_cycles(self):
        result = gen_markers(["x", "y"], markers=("o",), palette=("#a", "#b"))
        assert result["x"]["marker"] == "o"
        assert result["x"]["color"] == "#a"
        assert result["y"]["marker"] == "o"
        assert result["y"]["color"] == "#b"


class TestGenMarkersSeries:
    def test_returns_series(self):
        s = pd.Series(["A", "B"], name="g")
        result = gen_markers_series(s)
        assert isinstance(result, pd.Series)
        assert result.name == "g"
        assert len(result) == 2


class TestGenMarkersCrossGrouping:
    def test_returns_nested_dict(self):
        result = gen_markers_cross_grouping(["a", "b"], ["x", "y"])
        assert result["a"]["x"]["marker"]
        assert result["a"]["x"]["color"]
        assert result["b"]["y"]["marker"]

    def test_all_entries_have_marker_and_color(self):
        result = gen_markers_cross_grouping(["a", "b"], ["x", "y"])
        for g1 in ("a", "b"):
            for g2 in ("x", "y"):
                assert "marker" in result[g1][g2]
                assert "color" in result[g1][g2]

    def test_distinct_combinations(self):
        result = gen_markers_cross_grouping(["a", "b"], ["x", "y"])
        combos = {(result[g1][g2]["marker"], result[g1][g2]["color"]) for g1 in ("a", "b") for g2 in ("x", "y")}
        assert len(combos) == 4


class TestPipeline:
    def test_empty_pipeline_returns_unchanged(self):
        p = Pipeline()
        df = pd.DataFrame({"x": [1, 2, 3]})
        result = p.run(df)
        assert result is df

    def test_single_step(self):
        p = Pipeline()
        p.add("double", lambda d, **kw: d * 2)
        df = pd.DataFrame({"x": [1, 2]})
        result = p.run(df)
        assert result["x"].tolist() == [2, 4]

    def test_multiple_steps_chain(self):
        p = Pipeline()
        p.add("add_one", lambda d, **kw: d + 1)
        p.add("double", lambda d, **kw: d * 2)
        df = pd.DataFrame({"x": [1, 2]})
        result = p.run(df)
        assert result["x"].tolist() == [4, 6]

    def test_steps_property(self):
        p = Pipeline()
        p.add("step1", lambda d, **kw: d)
        p.add("step2", lambda d, **kw: d)
        assert len(p.steps) == 2
        assert p.steps[0].name == "step1"
        assert p.steps[1].name == "step2"

    def test_constructor_accepts_steps(self):
        step = PipelineStep(name="init", func=lambda d, **kw: d)
        p = Pipeline(steps=[step])
        assert len(p.steps) == 1

    def test_kwargs_passed_to_func(self):
        def multiply(df, **kw):
            return df * kw["factor"]
        p = Pipeline()
        p.add("mult", multiply, factor=3)
        df = pd.DataFrame({"x": [1, 2]})
        result = p.run(df)
        assert result["x"].tolist() == [3, 6]


class TestConstants:
    def test_default_markers(self):
        assert len(DEFAULT_MARKERS) == 12
        assert "o" in DEFAULT_MARKERS

    def test_default_palette(self):
        assert len(DEFAULT_PALETTE) == 10
        assert DEFAULT_PALETTE[0] == "#1f77b4"

    def test_io_exports(self):
        from geofig_engine.io import __all__
        assert "haversine" in __all__
        assert "path_distance" in __all__
        assert "gen_markers" in __all__
        assert "gen_markers_series" in __all__
        assert "Pipeline" in __all__
        assert "PipelineStep" in __all__
        assert "equisflat_to_sample_df" in __all__
        assert "sample_df_to_equisflat" in __all__
        assert "equis_crosstab_to_flat" in __all__
        assert "equisflat_normalize_units" in __all__
        assert "SI_PREFIXES" in __all__
        assert "ecesis_to_sample_df" in __all__
        assert "create_bins" in __all__


class TestEquisFlatToSample:
    def test_pivot_shape_and_values(self):
        flat = pd.DataFrame({
            "Location": ["A", "A", "B", "B"],
            "Parameter": ["NO3", "Cl", "NO3", "Cl"],
            "Result": [1.0, 2.0, 3.0, 4.0],
        })
        wide = equisflat_to_sample_df(flat)
        assert list(wide.columns) == ["Location", "NO3", "Cl"]
        assert len(wide) == 2
        by_loc = wide.set_index("Location")
        assert by_loc.loc["A", "NO3"] == 1.0
        assert by_loc.loc["B", "Cl"] == 4.0

    def test_parameter_columns_first_appearance_order(self):
        flat = pd.DataFrame({
            "Location": ["A", "A"],
            "Parameter": ["Cl", "NO3"],
            "Result": [1.0, 2.0],
        })
        wide = equisflat_to_sample_df(flat)
        assert list(wide.columns) == ["Location", "Cl", "NO3"]

    def test_custom_sample_keys(self):
        flat = pd.DataFrame({
            "Location": ["A", "A"],
            "Sample_Code": ["S1", "S1"],
            "Parameter": ["NO3", "Cl"],
            "Result": [1.0, 2.0],
        })
        wide = equisflat_to_sample_df(
            flat, sample_keys=("Location", "Sample_Code"))
        assert list(wide.columns) == ["Location", "Sample_Code", "NO3", "Cl"]

    def test_duplicate_sample_parameter_raises(self):
        flat = pd.DataFrame({
            "Location": ["A", "A"],
            "Parameter": ["NO3", "NO3"],
            "Result": [1.0, 2.0],
        })
        with pytest.raises(ValueError, match="duplicate result for parameter 'NO3'"):
            equisflat_to_sample_df(flat)

    def test_extra_cols_constant_carried(self):
        flat = pd.DataFrame({
            "Location": ["A", "A", "B", "B"],
            "Parameter": ["NO3", "Cl", "NO3", "Cl"],
            "Result": [1.0, 2.0, 3.0, 4.0],
            "Well_Type": ["W", "W", "X", "X"],
        })
        wide = equisflat_to_sample_df(flat, extra_cols=("Well_Type",))
        assert list(wide.columns) == ["Location", "NO3", "Cl", "Well_Type"]
        assert wide.set_index("Location").loc["A", "Well_Type"] == "W"

    def test_varying_extra_cols_raise(self):
        flat = pd.DataFrame({
            "Location": ["A", "A"],
            "Parameter": ["NO3", "Cl"],
            "Result": [1.0, 2.0],
            "Date": ["2026-01-01", "2026-02-01"],
        })
        with pytest.raises(ValueError, match="not constant per sample"):
            equisflat_to_sample_df(flat, extra_cols=("Date",))

    def test_drop_na(self):
        flat = pd.DataFrame({
            "Location": ["A", "A", "B", "B"],
            "Parameter": ["NO3", "Cl", "NO3", "Cl"],
            "Result": [1.0, np.nan, 3.0, 4.0],
        })
        wide = equisflat_to_sample_df(flat)
        by_loc = wide.set_index("Location")
        assert by_loc.loc["A", "NO3"] == 1.0
        assert by_loc.loc["B", "Cl"] == 4.0
        # drop_na removed the A/Cl row entirely → A/Cl cell is NaN
        assert np.isnan(by_loc.loc["A", "Cl"])
        wide_keep = equisflat_to_sample_df(flat, drop_na=False)
        assert np.isnan(wide_keep.set_index("Location").loc["A", "Cl"])

    def test_input_frame_unchanged(self):
        flat = pd.DataFrame({
            "Location": ["A", "A"],
            "Parameter": ["NO3", "Cl"],
            "Result": [1.0, 2.0],
        })
        snapshot = flat.copy()
        equisflat_to_sample_df(flat)
        pd.testing.assert_frame_equal(flat, snapshot)

    def test_missing_required_column_raises(self):
        flat = pd.DataFrame({"Location": ["A"], "Parameter": ["NO3"]})
        with pytest.raises(ValueError, match="missing required columns"):
            equisflat_to_sample_df(flat)


class TestSampleDfToEquisFlat:
    def test_melt_basic(self):
        wide = pd.DataFrame({
            "Location": ["A", "B"],
            "NO3": [1.0, 3.0],
            "Cl": [2.0, 4.0],
        })
        flat = sample_df_to_equisflat(wide)
        assert list(flat.columns) == ["Location", "Parameter", "Result"]
        assert len(flat) == 4

    def test_round_trip(self):
        flat = pd.DataFrame({
            "Location": ["A", "A", "B", "B"],
            "Parameter": ["Cl", "NO3", "Cl", "NO3"],
            "Result": [1.0, 2.0, 3.0, 4.0],
        })
        wide = equisflat_to_sample_df(flat)
        back = sample_df_to_equisflat(wide)
        expected = flat.sort_values(["Location", "Parameter"]).reset_index(drop=True)
        got = back.sort_values(["Location", "Parameter"]).reset_index(drop=True)
        pd.testing.assert_frame_equal(got, expected)

    def test_extra_cols_propagated(self):
        wide = pd.DataFrame({
            "Location": ["A"],
            "NO3": [1.0],
            "Well_Type": ["W"],
        })
        flat = sample_df_to_equisflat(wide, extra_cols=("Well_Type",))
        assert flat.iloc[0]["Well_Type"] == "W"

    def test_drop_na(self):
        wide = pd.DataFrame({"Location": ["A"], "NO3": [np.nan]})
        assert sample_df_to_equisflat(wide).empty
        assert len(sample_df_to_equisflat(wide, drop_na=False)) == 1


class TestEquisCrosstabToFlat:
    def test_underscore_units(self):
        ct = pd.DataFrame({
            "Location": ["A", "B"],
            "NO3_mg/L": [1.0, 2.0],
            "Ca_ug/L": [5.0, 6.0],
            "pH": [7.0, 8.0],
        })
        out = equis_crosstab_to_flat(ct)
        assert list(out.columns) == ["Location", "Parameter", "Result", "Result_Unit", "pH"]
        assert len(out) == 4
        rows = out.set_index(["Location", "Parameter"])
        assert rows.loc[("A", "NO3"), "Result"] == 1.0
        assert rows.loc[("A", "NO3"), "Result_Unit"] == "mg/L"
        assert rows.loc[("B", "Ca"), "Result_Unit"] == "ug/L"
        # unit-less metadata broadcast onto every row (one row per part, in
        # original row order: NO3-rows then Ca-rows, each with A then B)
        assert out["pH"].tolist() == [7.0, 8.0, 7.0, 8.0]

    def test_parenthesized_units(self):
        ct = pd.DataFrame({
            "Location": ["A"],
            "Ca (mg/L)": [5.0],
        })
        out = equis_crosstab_to_flat(ct)
        assert out.iloc[0]["Parameter"] == "Ca"
        assert out.iloc[0]["Result_Unit"] == "mg/L"
        assert out.iloc[0]["Result"] == 5.0

    def test_custom_keys_and_columns(self):
        ct = pd.DataFrame({
            "Sample_Code": ["S1"],
            "NO3_ppb": [10.0],
        })
        out = equis_crosstab_to_flat(
            ct, sample_keys=("Sample_Code",), parameter_col="Analyte",
            value_col="Value", unit_col="Unit")
        assert list(out.columns) == ["Sample_Code", "Analyte", "Value", "Unit"]
        assert out.iloc[0]["Unit"] == "ppb"

    def test_non_numeric_cell_becomes_nan(self):
        ct = pd.DataFrame({
            "Location": ["A", "B"],
            "NO3_mg/L": [1.0, "n.d."],
        })
        out = equis_crosstab_to_flat(ct)
        assert np.isnan(out.loc[out["Location"] == "B", "Result"].iloc[0])

    def test_no_unit_columns_raises(self):
        ct = pd.DataFrame({"Location": ["A"], "pH": [7.0]})
        with pytest.raises(ValueError, match="no analyte columns with unit suffixes"):
            equis_crosstab_to_flat(ct)

    def test_missing_sample_key_raises(self):
        ct = pd.DataFrame({"NO3_mg/L": [1.0]})
        with pytest.raises(ValueError, match="missing required columns"):
            equis_crosstab_to_flat(ct)

    def test_input_frame_unchanged(self):
        ct = pd.DataFrame({
            "Location": ["A"],
            "NO3_mg/L": [1.0],
        })
        snapshot = ct.copy()
        equis_crosstab_to_flat(ct)
        pd.testing.assert_frame_equal(ct, snapshot)

    def test_excel_input(self, tmp_path):
        pytest.importorskip("openpyxl")
        ct = pd.DataFrame({
            "Location": ["A", "B"],
            "NO3_mg/L": [1.0, 2.0],
            "Ca (mg/L)": [5.0, 6.0],
        })
        xlsx = tmp_path / "cross_tab.xlsx"
        ct.to_excel(xlsx, index=False)
        out = equis_crosstab_to_flat(xlsx)
        assert len(out) == 4
        rows = out.set_index(["Location", "Parameter"])
        assert rows.loc[("A", "NO3"), "Result"] == 1.0
        assert rows.loc[("B", "Ca"), "Result_Unit"] == "mg/L"


class TestEquisflatNormalizeUnits:
    def test_single_group_rescale(self):
        flat = pd.DataFrame({
            "Parameter": ["NO3"] * 4,
            "Result": [1.0, 1.0, 1.0, 1.0],
            "Result_Unit": ["ng/L", "ug/L", "mg/L", "g/L"],
        })
        out = equisflat_normalize_units(flat)
        # tie (1 occurrence each) → lexicographically smallest recognized unit
        assert out["Result_Unit"].tolist() == ["g/L"] * 4
        assert out["Result"].tolist() == [1e-9, 1e-6, 1e-3, 1.0]

    def test_majority_canonical(self):
        flat = pd.DataFrame({
            "Parameter": ["NO3"] * 3,
            "Result": [1.0, 1.0, 1000.0],
            "Result_Unit": ["mg/L", "mg/L", "ug/L"],
        })
        out = equisflat_normalize_units(flat)
        assert out["Result_Unit"].tolist() == ["mg/L"] * 3
        assert out["Result"].tolist() == [1.0, 1.0, 1.0]

    def test_inter_group_independence(self):
        flat = pd.DataFrame({
            "Parameter": ["Ca", "Ca", "NO3", "NO3", "NO3"],
            "Result": [1.0, 2.0, 1.0, 1.0, 1000.0],
            "Result_Unit": ["mg/L", "mg/L", "ug/L", "ug/L", "ng/L"],
        })
        out = equisflat_normalize_units(flat)
        # Ca keeps mg/L; NO3 canonical is ug/L (majority), ng/L row rescales
        assert out["Result_Unit"].tolist() == ["mg/L", "mg/L", "ug/L", "ug/L", "ug/L"]
        assert out["Result"].tolist() == [1.0, 2.0, 1.0, 1.0, 1.0]

    def test_tie_lexicographically_smallest(self):
        flat = pd.DataFrame({
            "Parameter": ["Na"] * 2,
            "Result": [1.0, 1.0],
            "Result_Unit": ["ug/L", "mg/L"],
        })
        out = equisflat_normalize_units(flat)
        assert out["Result_Unit"].tolist() == ["mg/L", "mg/L"]
        assert out["Result"].tolist() == [0.001, 1.0]

    def test_micro_sign_and_u_equivalent(self):
        flat = pd.DataFrame({
            "Parameter": ["NO3", "NO3"],
            "Result": [1.0, 1000.0],
            "Result_Unit": ["µg/L", "ug/L"],
        })
        out = equisflat_normalize_units(flat)
        assert out["Result_Unit"].tolist() == ["ug/L", "ug/L"]
        assert out["Result"].tolist() == [1.0, 1000.0]

    def test_unrecognized_units_untouched(self):
        flat = pd.DataFrame({
            "Parameter": ["pH", "pH"],
            "Result": [7.2, 0.5],
            "Result_Unit": ["N/A", "ppb"],
        })
        out = equisflat_normalize_units(flat)
        pd.testing.assert_frame_equal(out, flat)

    def test_unrecognized_rows_untouched_in_mixed_group(self):
        flat = pd.DataFrame({
            "Parameter": ["NO3", "NO3", "NO3"],
            "Result": [1.0, "n.d.", 1.0],
            "Result_Unit": ["mg/L", "ppb", "mg/L"],
        })
        out = equisflat_normalize_units(flat)
        assert out["Result_Unit"].tolist() == ["mg/L", "ppb", "mg/L"]
        assert out["Result"].tolist() == [1.0, "n.d.", 1.0]

    def test_nan_unit_row_untouched(self):
        flat = pd.DataFrame({
            "Parameter": ["NO3", "NO3"],
            "Result": [1.0, 2.0],
            "Result_Unit": ["mg/L", None],
        })
        out = equisflat_normalize_units(flat)
        assert out["Result_Unit"].tolist() == ["mg/L", None]
        assert out["Result"].tolist() == [1.0, 2.0]

    def test_custom_column_names(self):
        flat = pd.DataFrame({
            "Analyte": ["NO3", "NO3"],
            "Value": [1000.0, 1.0],
            "Unit": ["ug/L", "mg/L"],
        })
        out = equisflat_normalize_units(
            flat, parameter_col="Analyte", value_col="Value", unit_col="Unit")
        assert out["Unit"].tolist() == ["mg/L", "mg/L"]
        assert out["Value"].tolist() == [1.0, 1.0]

    def test_inplace_mutates_and_returns_input(self):
        flat = pd.DataFrame({
            "Parameter": ["NO3", "NO3"],
            "Result": [1000.0, 1.0],
            "Result_Unit": ["ug/L", "mg/L"],
        })
        out = equisflat_normalize_units(flat, inplace=True)
        assert out is flat
        assert flat["Result_Unit"].tolist() == ["mg/L", "mg/L"]
        assert flat["Result"].tolist() == [1.0, 1.0]

    def test_input_not_mutated_by_default(self):
        flat = pd.DataFrame({
            "Parameter": ["NO3", "NO3"],
            "Result": [1000.0, 1.0],
            "Result_Unit": ["ug/L", "mg/L"],
        })
        snapshot = flat.copy()
        equisflat_normalize_units(flat)
        pd.testing.assert_frame_equal(flat, snapshot)

    def test_missing_column_raises(self):
        flat = pd.DataFrame({"Parameter": ["NO3"], "Result": [1.0]})
        with pytest.raises(ValueError, match="missing required columns"):
            equisflat_normalize_units(flat)


class TestEcesisToSampleDf:
    def test_underscore_and_paren_units(self):
        frame = pd.DataFrame({
            "NO3_mg/L": [1.0, 2.0],
            "Ca (mg/L)": [5.0, 6.0],
            "Sample_ID": ["S1", "S2"],
            "pH": [7.0, 8.0],
        })
        out = ecesis_to_sample_df(frame)
        assert list(out.columns) == [
            ("NO3", "mg/L"), ("Ca", "mg/L"), ("Sample_ID", ""), ("pH", ""),
        ]
        assert out[("NO3", "mg/L")].tolist() == [1.0, 2.0]
        assert out[("Ca", "mg/L")].tolist() == [5.0, 6.0]
        assert out[("Sample_ID", "")].tolist() == ["S1", "S2"]

    def test_row_and_column_order_preserved(self):
        frame = pd.DataFrame({
            "B_mg/L": [3.0, 4.0],
            "A_ug/L": [1.0, 2.0],
        }, index=[10, 20])
        out = ecesis_to_sample_df(frame)
        assert list(out.columns) == [("B", "mg/L"), ("A", "ug/L")]
        assert out.index.tolist() == [10, 20]

    def test_numeric_coercion(self):
        frame = pd.DataFrame({"NO3_mg/L": ["1.5", "n.d.", 2]})
        out = ecesis_to_sample_df(frame, drop_na=False)
        got = out[("NO3", "mg/L")].tolist()
        assert got[0] == 1.5
        assert np.isnan(got[1])
        assert got[2] == 2.0

    def test_plain_column_values_not_coerced(self):
        frame = pd.DataFrame({"Sample_ID": ["S-001", "S-002"]})
        out = ecesis_to_sample_df(frame)
        assert out[("Sample_ID", "")].tolist() == ["S-001", "S-002"]

    def test_drop_na_all_parsed_nan(self):
        frame = pd.DataFrame({
            "NO3_mg/L": [1.0, np.nan, 3.0],
            "Ca_ug/L": [5.0, np.nan, "n.d."],
            "Sample_ID": ["S1", "S2", "S3"],
        })
        out = ecesis_to_sample_df(frame)
        assert len(out) == 2  # S2 row has NaN in every parsed cell → dropped
        assert out[("Sample_ID", "")].tolist() == ["S1", "S3"]

    def test_drop_na_false_keeps_all(self):
        frame = pd.DataFrame({
            "NO3_mg/L": [np.nan],
            "Sample_ID": ["S1"],
        })
        out = ecesis_to_sample_df(frame, drop_na=False)
        assert len(out) == 1

    def test_no_parsed_columns_nothing_dropped(self):
        frame = pd.DataFrame({"Sample_ID": ["S1", "S2"]})
        out = ecesis_to_sample_df(frame)
        assert len(out) == 2

    def test_duplicate_parsed_key_raises(self):
        frame2 = pd.DataFrame({
            "NO3_mg/L": [1.0],
            "NO3 (mg/L)": [2.0],
        })
        with pytest.raises(ValueError, match="duplicate.*column keys"):
            ecesis_to_sample_df(frame2)

    def test_custom_unit_pattern(self):
        frame = pd.DataFrame({"Temp_degC": [20.0], "NO3_mg/L": [1.0]})
        pattern = re.compile(r"^(?P<param>.+?)_(?P<unit>degC)$")
        out = ecesis_to_sample_df(frame, unit_pattern=pattern)
        assert list(out.columns) == [("Temp", "degC"), ("NO3_mg/L", "")]

    def test_custom_pattern_missing_group_raises(self):
        bad = re.compile(r"^(?P<param>.+)$")  # matches but lacks 'unit'
        with pytest.raises(ValueError, match="'param' and 'unit'"):
            ecesis_to_sample_df(
                pd.DataFrame({"NO3_mg/L": [1.0]}), unit_pattern=bad)

    def test_input_frame_unchanged(self):
        frame = pd.DataFrame({
            "NO3_mg/L": [1.0, 2.0],
            "Sample_ID": ["S1", "S2"],
        })
        snapshot = frame.copy()
        ecesis_to_sample_df(frame)
        pd.testing.assert_frame_equal(frame, snapshot)


class TestCreateBins:
    def test_range_int_equal_width(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0], name="NO3")
        out = create_bins(s, bins=2)
        assert out.name == "NO3"
        assert out.isna().sum() == 0
        # include_lowest=True → min falls in first bin
        assert out.iloc[0] == out.iloc[1]
        assert out.iloc[2] == out.iloc[3]

    def test_range_explicit_edges_with_labels(self):
        s = pd.Series([1.0, 5.0, 9.0])
        out = create_bins(s, bins=[0, 5, 10], labels=["low", "high"])
        assert out.tolist() == ["low", "low", "high"]

    def test_range_datetime(self):
        s = pd.to_datetime(pd.Series(
            ["2026-01-01", "2026-04-01", "2026-07-01", "2026-10-01"]))
        out = create_bins(s, bins=2)
        assert out.isna().sum() == 0
        assert out.dtype.name.startswith("category")

    def test_quantile_equal_frequency(self):
        s = pd.Series(range(1, 11), name="v")
        out = create_bins(s, bins=5, strategy="quantile")
        counts = out.value_counts().tolist()
        assert counts == [2, 2, 2, 2, 2]

    def test_quantile_duplicate_edges_collapsed(self):
        s = pd.Series([1, 1, 1, 1, 2, 3, 4, 5])
        out = create_bins(s, bins=4, strategy="quantile")
        assert out.isna().sum() == 0
        # duplicated edges collapsed → fewer than requested bins, none empty
        assert len(out.cat.categories) < 4

    def test_quantile_datetime(self):
        s = pd.to_datetime(pd.Series(
            ["2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01",
             "2026-05-01", "2026-06-01"]))
        out = create_bins(s, bins=3, strategy="quantile")
        assert out.isna().sum() == 0
        assert out.dtype.name.startswith("category")

    def test_nan_to_nan_category(self):
        s = pd.Series([1.0, np.nan, 3.0, np.nan])
        out = create_bins(s, bins=2)
        assert out.isna().tolist() == [False, True, False, True]

    def test_deterministic(self):
        s = pd.Series([0.1, 0.5, 0.9, 1.3, 1.7, 2.1, 2.5])
        a = create_bins(s, bins=3)
        b = create_bins(s, bins=3)
        pd.testing.assert_series_equal(a, b)
        assert a.cat.categories.dtype == b.cat.categories.dtype

    def test_input_not_mutated(self):
        s = pd.Series([1.0, 2.0, 3.0, np.nan])
        snapshot = s.copy()
        create_bins(s, bins=2)
        pd.testing.assert_series_equal(s, snapshot)

    def test_quantile_labels_applied(self):
        s = pd.Series(range(1, 11))
        out = create_bins(s, bins=5, strategy="quantile",
                          labels=["q1", "q2", "q3", "q4", "q5"])
        assert set(out.cat.categories.tolist()) == {"q1", "q2", "q3", "q4", "q5"}

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="unknown strategy"):
            create_bins(pd.Series([1, 2, 3]), bins=2, strategy="bogus")
