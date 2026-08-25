"""
Tests for StatIonFractions: concentration addition + percent normalization
emitting fixed-slot fraction columns and diamond coordinates (Phase 14.5 WP3).

Parity anchor: the legacy piper template math in templates/piper.py
(``_cat_fracs`` / ``_ternary_x`` / ``_ternary_y`` / ``_diamond_xy``).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from geofig_engine.core.geom import GeomPoint
from geofig_engine.core.layer import Layer
from geofig_engine.core.stat import StatIonFractions
from geofig_engine.serialize import stat_from_dict, stat_to_dict


def _sample_df():
    """Two normal samples + one zero-total row + one row with a missing ion."""
    return pd.DataFrame({
        "Ca": [1.0, 0.5, 0.0, 1.0],
        "Mg": [1.0, 0.25, 0.0, np.nan],
        "Na": [1.0, 0.25, 0.0, 3.0],
        "K": [1.0, 0.0, 0.0, 1.0],
        "HCO3": [2.0, 0.4, 0.0, 2.0],
        "CO3": [0.0, 0.1, 0.0, np.nan],
        "SO4": [1.0, 0.25, 0.0, 1.0],
        "Cl": [1.0, 0.25, 0.0, 1.0],
    })


def _default_stat():
    return StatIonFractions(
        cations=(("Ca",), ("Mg",), ("Na", "K")),
        anions=(("HCO3", "CO3"), ("SO4",), ("Cl",)),
    )


# ---------------------------------------------------------------------------
# Hand-computed chemistry
# ---------------------------------------------------------------------------


class TestHandComputed:
    def test_slot_fractions_symmetric_sample(self):
        # Sample 0: Ca=1, Mg=1, Na+K=2 -> total 4 -> (.25, .25, .5)
        #           HCO3+CO3=2, SO4=1, Cl=1 -> total 4 -> (.5, .25, .25)
        df = _sample_df().iloc[[0]].reset_index(drop=True)
        out = _default_stat().compute(df)
        assert out["cation_f0"].iloc[0] == pytest.approx(0.25)
        assert out["cation_f1"].iloc[0] == pytest.approx(0.25)
        assert out["cation_f2"].iloc[0] == pytest.approx(0.50)
        assert out["anion_f0"].iloc[0] == pytest.approx(0.50)
        assert out["anion_f1"].iloc[0] == pytest.approx(0.25)
        assert out["anion_f2"].iloc[0] == pytest.approx(0.25)

    def test_diamond_center_for_balanced_sample(self):
        # With cat_x = f2 + f1/2 = .625, an_x = .375, equal heights,
        # the diamond formulas give exactly (0, 0) for sample 0.
        df = _sample_df().iloc[[0]].reset_index(drop=True)
        out = _default_stat().compute(df)
        assert out["diamond_x"].iloc[0] == pytest.approx(0.0, abs=1e-12)
        assert out["diamond_y"].iloc[0] == pytest.approx(0.0, abs=1e-12)

    def test_single_ion_columns(self):
        # Pre-combined columns passed as plain strings.
        df = pd.DataFrame({
            "Ca": [3.0], "Mg": [1.0], "NaK": [2.0],
            "Alk": [4.0], "SO4": [2.0], "Cl": [2.0],
        })
        out = StatIonFractions(
            cations=("Ca", "Mg", "NaK"), anions=("Alk", "SO4", "Cl")
        ).compute(df)
        assert out["cation_f0"].iloc[0] == pytest.approx(0.5)
        assert out["cation_f1"].iloc[0] == pytest.approx(1.0 / 6.0)
        assert out["cation_f2"].iloc[0] == pytest.approx(1.0 / 3.0)
        assert out["anion_f0"].iloc[0] == pytest.approx(0.5)
        assert out["anion_f1"].iloc[0] == pytest.approx(0.25)
        assert out["anion_f2"].iloc[0] == pytest.approx(0.25)

    def test_na_k_grouping_sums_columns(self):
        df = pd.DataFrame({
            "Ca": [1.0], "Mg": [1.0], "Na": [1.0], "K": [1.0],
            "HCO3": [4.0], "CO3": [0.0], "SO4": [2.0], "Cl": [2.0],
        })
        out = _default_stat().compute(df)
        # Na+K slot = 2 of cation total 4
        assert out["cation_f2"].iloc[0] == pytest.approx(0.5)
        # anions: HCO3+CO3=4, SO4=2, Cl=2 of total 8 -> (.5, .25, .25)
        assert out["anion_f0"].iloc[0] == pytest.approx(0.5)
        assert out["anion_f1"].iloc[0] == pytest.approx(0.25)
        assert out["anion_f2"].iloc[0] == pytest.approx(0.25)

    def test_hco3_co3_grouping_sums_columns(self):
        df = pd.DataFrame({
            "Ca": [1.0], "Mg": [1.0], "Na": [0.0], "K": [0.0],
            "HCO3": [1.0], "CO3": [1.0], "SO4": [1.0], "Cl": [1.0],
        })
        out = _default_stat().compute(df)
        # HCO3+CO3 = 2 of anion total 4
        assert out["anion_f0"].iloc[0] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Degenerate-row policy (mirrors legacy fillna(0)/nan_to_num)
# ---------------------------------------------------------------------------


class TestDegenerateRows:
    def test_zero_total_row_gives_all_zero_fractions(self):
        df = _sample_df()
        out = _default_stat().compute(df)
        zero_row = out.iloc[2]
        for col in ("cation_f0", "cation_f1", "cation_f2",
                    "anion_f0", "anion_f1", "anion_f2"):
            assert zero_row[col] == 0.0
        # Diamond position mirrors the legacy pipeline exactly: all-zero
        # fractions leave dx = ... - 0.5, i.e. the diamond's left vertex.
        assert zero_row["diamond_x"] == pytest.approx(-0.5)
        assert zero_row["diamond_y"] == pytest.approx(0.0)

    def test_missing_ion_treated_as_zero(self):
        # Row 3 has Mg=NaN, CO3=NaN; remaining ions still fraction correctly.
        df = _sample_df()
        out = _default_stat().compute(df)
        row = out.iloc[3]
        # cation total = Ca 1 + Na/K 4 = 5 -> f = (.2, 0, .8)
        assert row["cation_f0"] == pytest.approx(0.2)
        assert row["cation_f1"] == 0.0
        assert row["cation_f2"] == pytest.approx(0.8)
        # anion total = HCO3 2 + SO4 1 + Cl 1 = 4 (CO3 NaN skipped)
        assert row["anion_f0"] == pytest.approx(0.5)

    def test_output_has_no_nan_or_inf(self):
        out = _default_stat().compute(_sample_df())
        arr = out.to_numpy(dtype=float)
        assert np.isfinite(arr).all()


# ---------------------------------------------------------------------------
# Legacy parity
# ---------------------------------------------------------------------------


class TestLegacyParity:
    def test_matches_piper_template_math(self):
        """StatIonFractions output matches the legacy piper math (now inlined)."""
        import math

        df = _sample_df()
        df = df.copy()
        df["NaK"] = df["Na"] + df["K"]

        def _cat_fracs(data, cols):
            total = data[list(cols)].sum(axis=1)
            return [data[c] / total for c in cols]

        def _ternary_x(f1, f0):
            return f1.fillna(0).values * 1.0 + f0.fillna(0).values * 0.5

        def _ternary_y(f0):
            sx = math.sqrt(3) / 2.0
            return f0.fillna(0).values * sx

        def _diamond_xy(cat_x, cat_y, an_x, an_y):
            h = 0.5 * math.sqrt(3)
            dx = an_y / (4 * h) + 0.5 * an_x - cat_y / (4 * h) + 0.5 * cat_x - 0.5
            dy = 0.5 * an_y + h * an_x + 0.5 * cat_y - h * cat_x
            return np.nan_to_num(dx), np.nan_to_num(dy)

        ca_f, mg_f, nak_f = _cat_fracs(df, ("Ca", "Mg", "NaK"))
        hco3_f, so4_f, cl_f = _cat_fracs(df, ("HCO3", "SO4", "Cl"))
        cat_x = _ternary_x(nak_f, mg_f)
        cat_y = _ternary_y(mg_f)
        an_x = _ternary_x(cl_f, so4_f)
        an_y = _ternary_y(so4_f)
        exp_dx, exp_dy = _diamond_xy(cat_x, cat_y, an_x, an_y)

        out = StatIonFractions(
            cations=("Ca", "Mg", "NaK"),
            anions=("HCO3", "SO4", "Cl"),
        ).compute(df)

        np.testing.assert_allclose(out["diamond_x"], exp_dx, atol=1e-12)
        np.testing.assert_allclose(out["diamond_y"], exp_dy, atol=1e-12)
        # Ternary positions reconstructible from slots with same convention
        np.testing.assert_allclose(
            out["cation_f2"] + 0.5 * out["cation_f1"], cat_x, atol=1e-12
        )
        np.testing.assert_allclose(
            (np.sqrt(3) / 2) * out["cation_f1"], cat_y, atol=1e-12
        )

    def test_legacy_column_defaults_align(self):
        # Default groups mirror PiperCoord's left/right triangle conventions.
        stat = StatIonFractions()
        assert [list(g) for g in stat.cation_groups] == [["Ca"], ["Mg"], ["Na", "K"]]
        assert [list(g) for g in stat.anion_groups] == [["HCO3", "CO3"], ["SO4"], ["Cl"]]


# ---------------------------------------------------------------------------
# Purity & validation
# ---------------------------------------------------------------------------


class TestPurityAndValidation:
    def test_compute_is_pure(self):
        stat = _default_stat()
        df = _sample_df()
        snapshot = df.copy(deep=True)
        first = stat.compute(df)
        second = stat.compute(df)
        pd.testing.assert_frame_equal(first, second)
        pd.testing.assert_frame_equal(df, snapshot)  # input untouched

    def test_index_preserved(self):
        idx = pd.Index([7, 8, 9, 10])
        df = _sample_df()
        df.index = idx
        out = _default_stat().compute(df)
        assert list(out.index) == list(idx)

    def test_missing_columns_raise_with_names(self):
        df = pd.DataFrame({"Ca": [1.0]})
        with pytest.raises(ValueError, match=r"missing columns.*\['Mg'"):
            _default_stat().compute(df)

    def test_wrong_slot_count_raises(self):
        with pytest.raises(ValueError, match="exactly three"):
            StatIonFractions(cations=("Ca", "Mg"))

    def test_bad_slot_value_raises(self):
        with pytest.raises(ValueError, match="slots must be"):
            StatIonFractions(cations=("Ca", "Mg", 42))

    def test_non_sequence_raises(self):
        with pytest.raises(TypeError, match="sequence of three"):
            StatIonFractions(cations="Ca")


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_params_json_shape(self):
        d = stat_to_dict(_default_stat())
        assert d == {
            "type": "ion_fractions",
            "params": {
                "cations": [["Ca"], ["Mg"], ["Na", "K"]],
                "anions": [["HCO3", "CO3"], ["SO4"], ["Cl"]],
            },
        }

    def test_roundtrip_default(self):
        restored = stat_from_dict(stat_to_dict(_default_stat()))
        assert isinstance(restored, StatIonFractions)
        assert restored.params == _default_stat().params
        pd.testing.assert_frame_equal(restored.compute(_sample_df()), _default_stat().compute(_sample_df()))

    def test_roundtrip_custom_groups(self):
        stat = StatIonFractions(cations=("Ca", ("Mg", "Sr"), "NaK"))
        restored = stat_from_dict(stat_to_dict(stat))
        assert restored.cation_groups == (("Ca",), ("Mg", "Sr"), ("NaK",))


# ---------------------------------------------------------------------------
# Generator routing: three layers sharing ONE instance
# ---------------------------------------------------------------------------


class TestSharedInstanceRouting:
    def test_three_layers_share_one_stat_instance(self):
        from geofig_engine.core.dataset import Dataset
        from geofig_engine.engine.generator import FigureEngine

        stat = _default_stat()
        layers = [
            Layer(geom=GeomPoint(), stat=stat,
                  mapping={"x": "cation_f0", "y": "cation_f1"}, zorder=10),
            Layer(geom=GeomPoint(), stat=stat,
                  mapping={"x": "anion_f0", "y": "anion_f2"}),
            Layer(geom=GeomPoint(), stat=stat,
                  mapping={"x": "diamond_x", "y": "diamond_y"}),
        ]
        df = _sample_df()
        engine = FigureEngine()
        specs = engine.build_specs_from_layers(
            Dataset(dataframe=df, key_column=df.columns[0]), layers
        )
        spec = specs[0]

        # Same instance attached to every layer spec
        assert spec.layers[0].stat is stat
        assert spec.layers[1].stat is stat
        assert spec.layers[2].stat is stat

        # Mapping strings resolved to identical stat-output series
        expected = stat.compute(df)
        vm0, vm1, vm2 = (l.visual_mapping for l in spec.layers)
        pd.testing.assert_series_equal(vm0["x"], expected["cation_f0"])
        pd.testing.assert_series_equal(vm1["y"], expected["anion_f2"])
        pd.testing.assert_series_equal(vm2["x"], expected["diamond_x"])
        pd.testing.assert_series_equal(vm2["y"], expected["diamond_y"])

    def test_non_stat_columns_fall_back_to_original_data(self):
        from geofig_engine.core.dataset import Dataset
        from geofig_engine.engine.generator import FigureEngine

        stat = _default_stat()
        layer = Layer(geom=GeomPoint(), stat=stat,
                      mapping={"x": "diamond_x", "y": "diamond_y", "color": "Ca"})
        specs = FigureEngine().build_specs_from_layers(
            Dataset(dataframe=_sample_df(), key_column="Ca"), [layer]
        )
        vm = specs[0].layers[0].visual_mapping
        pd.testing.assert_series_equal(vm["color"], _sample_df()["Ca"])
