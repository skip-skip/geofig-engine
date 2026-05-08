TODO:
- Refactor Dimension/Column indexing
- Build engine/renderer/datacore wrapper
- Implement scaling (log vs normal) to bivariate template
- Linear color ramp bivariate
X Implement linear modeling (ex meteoric lines, compliance lines, etc.)
X Implement timeseries (data aggregation handled by user)
- Implement secondary y-axis and data ingestion
- Legend generator (treat legend as figure)

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