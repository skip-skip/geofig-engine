Architecture constraints:

- Dataset must not depend on rendering
- Dimension metadata must not contain plotting logic
- AttributeMapping must be declarative only
- FigureSpec must be renderer-agnostic
- IteratorEngine must not depend on templates or rendering
- Renderer must not perform data transformations

DimensionSelectors must resolve to column names before rendering.

Templates must only define structure and defaults.