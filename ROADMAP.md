TODO:
- Linear color ramp bivariate
- Legend generator (treat legend as figure, preserve visual mappings across renders)
- add layers
    - step line, histo, bar
    - box, violin
    - grid, heatmap, hexgrid, image
    - contour
    - integral
    - area
- multithread iteration processing

FUTURE IMPLEMENTATIONS:
- Preprocessing data pipeline
    - Assign new columns / groups
- Render figures on pages

Figure examples (Jupyter Implementations):
- GW dataset
    - one analyte vs another
        - each unique sample -> symbol
        - color -> upgradient vs downgradient
    - all analytes vs all analytes (iterative version)
        - same formatting conditions as above
    - Build group column from well lists (with default pandas features)
        - each unique sample -> symbol
        - color -> group
- Waste rock dataset
    - PREREQ: color ramp implementation
    - plot sulf v iron
        - grade color by depth
- Gauge station dataset
    - plot water level v time
    - plot cond v time as second y axis
- Isotope plots
    - reference database of standards
    - select standards to render with data.