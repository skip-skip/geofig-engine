"""Tests for position adjustment utilities."""

from geofig_engine.renderers.matplotlib.position import dodge_positions


class TestDodgePositions:
    def test_single_series_centered(self):
        pos, width = dodge_positions(group_center=1.0, series_idx=0, n_series=1, total_width=0.8)
        assert pos == 1.0
        assert width == 0.85 * 0.8

    def test_two_series_symmetric(self):
        pos0, w0 = dodge_positions(1.0, 0, 2, 0.8)
        pos1, w1 = dodge_positions(1.0, 1, 2, 0.8)
        assert abs(pos0 - 1.0) == abs(pos1 - 1.0)
        assert pos0 < 1.0 < pos1
        assert w0 == w1

    def test_three_series_positions(self):
        pos0, _ = dodge_positions(1.0, 0, 3, 0.8)
        pos1, _ = dodge_positions(1.0, 1, 3, 0.8)
        pos2, _ = dodge_positions(1.0, 2, 3, 0.8)
        assert pos0 < pos1 < pos2
        assert pos1 == 1.0  # middle series centered

    def test_width_scales_with_total_width(self):
        _, w_small = dodge_positions(1.0, 0, 2, 0.6)
        _, w_large = dodge_positions(1.0, 0, 2, 1.0)
        assert w_small < w_large
