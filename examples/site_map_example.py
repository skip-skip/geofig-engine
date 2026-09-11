"""Example: render the ``site_map`` registry template (Phase 15, wp9).

Builds a synthetic property view — a site boundary polygon (flagged rows in the
same frame, with a NaN separator row to split multipart rings) plus well-sample
points with ``longitude``/``latitude`` coordinates, a ``facility`` grouping
column and well names — and renders it through the canonical entry point:

    render_template(df, template="site_map", ...)

No mapping is required: coordinates, the group column and the label column
auto-resolve from the frame. A second call shows the ``color`` mapping override
(coloring points by facility). Both calls also paint an XYZ tile basemap
(Esri WorldImagery, wp14) beneath the boundary/points/labels — override with
``settings={"basemap": {"provider": ..., "zoom": ..., "alpha": ...}}`` or
disable with ``{"basemap": None}``; a tile-server failure degrades to a
tile-free render with a warning.

Elevation contours (18.2) render **on by default**: a lazy terrarium DEM
fetch for the frame's lon/lat extent (10% buffer, bbox-keyed cache) feeds
the contour layer above the basemap and below the boundary ring, at the
old-geomapper defaults (10 m interval, white, alpha 0.6). Offline/HTTP/DEM
failures degrade to a warning + no contours. Contours are configured at the
**builder** level — the second call demonstrates an override dict; disable
entirely with ``site_map_builder(settings={"contours": None})``. Output goes
to examples/outputs/site_map_output as ``001.png`` / ``002.png`` plus the
grouped ``legend.png``.
"""

from pathlib import Path

import pandas as pd

from geofig_engine.engine import render_template
from geofig_engine.templates.site_map import site_map_builder

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
        # Basemap is on by default; this explicit dict shows the override
        # shape (image tiles at 55% opacity) and keeps the Esri default.
        "basemap": {"alpha": 0.55},
        # Elevation contours (18.2) are on by default too — a lazy terrarium
        # DEM fetch for this frame's lon/lat extent (10% buffer, bbox-keyed
        # cache); offline/HTTP/DEM failures degrade to a warning + no
        # contour lines. The override dict is demonstrated in the second
        # call (contour config is builder-level).
    },
    savedir=output_dir,
)
print(f"Rendered {len(figures)} figure(s) -> {output_dir}")

facility_figures = render_template(
    data=view,
    # Contour config is a builder-level setting (render_template's settings
    # merge onto the recipe at render time, so layer-shaping options like
    # "contours" / "contours": None are passed here): {"interval": 5,
    # "alpha": 0.5} merge over the old-geomapper defaults (white, 0.5 pt);
    # {"contours": None} would omit the layer entirely.
    template=site_map_builder(
        settings={"contours": {"interval": 5, "color": "white", "alpha": 0.5}}
    ),
    mapping={"color": "facility"},
    settings={"title": "Wells by Facility"},
    savedir=facility_dir,
)
print(f"Rendered {len(facility_figures)} figure(s) (facility coloring) -> {facility_dir}")

print("Done. See examples/outputs/site_map_output/ and site_map_output_facility/.")