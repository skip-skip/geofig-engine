"""Example: render the ``site_map`` registry template (Phase 15, wp9).

Builds a synthetic property view — a site boundary polygon (flagged rows in the
same frame, with a NaN separator row to split multipart rings) plus well-sample
points with ``longitude``/``latitude`` coordinates, a ``facility`` grouping
column and well names — and renders it through the canonical entry point:

    render_template(df, template="site_map", ...)

No mapping is required: coordinates, the group column and the label column
auto-resolve from the frame. A second call shows the ``color`` mapping override
(coloring points by facility). Output goes to examples/outputs/site_map_output as
``001.png`` / ``002.png`` plus the grouped ``legend.png``.
"""

from pathlib import Path

import pandas as pd

from geofig_engine.engine import render_template

output_dir = Path(__file__).resolve().parent / "outputs" / "site_map_output"
facility_dir = output_dir.parent / "site_map_output_facility"

boundary_ring = pd.DataFrame(
    {
        "longitude": [
            -116.6500, -116.4500, -116.4000, -116.3000, -116.1500,
            -116.2000, -116.6500,
        ],
        "latitude": [
            41.3200, 41.3500, 41.2200, 41.3600, 41.2800,
            41.1800, 41.3200,
        ],
# Site property boundary: first vertex repeated at the end so the ring
    # is closed. The renderer draws exactly the flagged rows.
    "boundary": [1, 1, 1, 1, 1, 1, 1],
    }
)

wells = pd.DataFrame(
    {
        "longitude": [-116.55, -116.48, -116.42, -116.36, -116.30, -116.24],
        "latitude": [41.31, 41.27, 41.33, 41.29, 41.25, 41.31],
        "facility": ["Plant A", "Plant A", "Plant A", "Plant B", "Plant B", "Plant B"],
        "name": ["MW-1", "MW-2", "MW-3", "MW-4", "MW-5", "MW-6"],
    }
)

# Property view: one frame, boundary rows flagged, sample rows unflagged.
view = pd.concat([boundary_ring, wells], ignore_index=True)

figures = render_template(
    data=view,
    template="site_map",
    settings={
        "title": "Haley & Aldrich Site — MW Network",
    },
    savedir=output_dir,
)
print(f"Rendered {len(figures)} figure(s) -> {output_dir}")

facility_figures = render_template(
    data=view,
    template="site_map",
    mapping={"color": "facility"},
    settings={
        "title": "Wells by Facility",
    },
    savedir=facility_dir,
)
print(f"Rendered {len(facility_figures)} figure(s) (facility coloring) -> {facility_dir}")

print("Done. See examples/outputs/site_map_output/ and site_map_output_facility/.")