"""
Isotope figure template for FigEngine.

Defines the contract for two-dimensional isotope plots with optional
color and marker encodings. Uses the function registry for water isotope
reference lines (GMWL, LMWL, etc.).
"""

from collections.abc import Sequence

from geofig_engine.data import (
    get_function_registry,
    FunctionCategory,
    FunctionType,
    FunctionLoadError,
)
from geofig_engine.layers.function_line import FunctionLineLayer
from geofig_engine.layers.scatter import ScatterLayer
from geofig_engine.templates.base import FigureTemplate
from geofig_engine.utils.typing import Mapping


class IsotopeTemplate(FigureTemplate):
    """
    Isotope template for creating 2D isotope ratio plots.

    Declares accepted function categories and types, validates functions
    from the registry, and builds visualization layers.
    """

    # Declare what functions this template accepts
    ACCEPTED_CATEGORIES = [FunctionCategory.WATER_ISOTOPE]
    ACCEPTED_TYPES = [FunctionType.LINEAR]
    REQUIRED_VARIABLES = ("x",)

    def __init__(
        self,
        functions: Sequence[str] | None = None,
        auto_filter: bool = True,
    ) -> None:
        """
        Initialize isotope template with reference water lines.

        Args:
            functions: Specific function IDs to include (e.g., ["GMWL", "ID_FALLS"]).
                      Must be WATER_ISOTOPE category and LINEAR type.
                      If None and auto_filter=True, auto-loads all matching functions.
            auto_filter: If True and no functions specified, auto-loads all
                        WATER_ISOTOPE/LINEAR functions from registry.

        Raises:
            ValueError: If function doesn't match accepted categories/types or
                       loading fails.
        """
        try:
            registry = get_function_registry()
            line_layers = []

            # Determine which functions to use
            if functions is None and auto_filter:
                # Auto-filter: all water isotope linear functions
                selected_functions = registry.filter(
                    category=FunctionCategory.WATER_ISOTOPE,
                    func_type=FunctionType.LINEAR,
                )
            elif functions is not None:
                # Explicit function IDs
                selected_functions = []
                for func_id in functions:
                    math_func = registry.get(func_id)

                    # Validate function meets template requirements
                    if math_func.category not in self.ACCEPTED_CATEGORIES:
                        raise ValueError(
                            f"Function '{func_id}' category '{math_func.category.value}' "
                            f"not accepted. Requires: {[c.value for c in self.ACCEPTED_CATEGORIES]}"
                        )
                    if math_func.func_type not in self.ACCEPTED_TYPES:
                        raise ValueError(
                            f"Function '{func_id}' type '{math_func.func_type.value}' "
                            f"not accepted. Requires: {[t.value for t in self.ACCEPTED_TYPES]}"
                        )
                    if not all(v in math_func.variables for v in self.REQUIRED_VARIABLES):
                        raise ValueError(
                            f"Function '{func_id}' missing required variables: {self.REQUIRED_VARIABLES}"
                        )

                    selected_functions.append(math_func)
            else:
                selected_functions = []

            # Build function line layers
            for math_func in selected_functions:
                line_layers.append(
                    FunctionLineLayer(
                        func=math_func.expression,
                        color=math_func.color,
                        style=math_func.linestyle,
                        label=math_func.label,
                    )
                )

        except FunctionLoadError as e:
            raise ValueError(f"Failed to load functions: {e}") from e
        except KeyError as e:
            raise ValueError(f"Unknown function ID: {e}") from e

        super().__init__(
            name="isotope",
            required_mappings=(Mapping.DEUTERIUM.value, Mapping.OXYGEN_18.value),
            optional_mappings=(
                Mapping.COLOR.value,
                Mapping.MARKER.value,
                Mapping.SIZE.value,
                Mapping.ALPHA.value,
            ),
            default_settings={
                "figsize": (10, 6),
                "xscale": "linear",
                "yscale": "linear",
                "grid": True,
                "figname": None,
            },
            projection=FigureTemplate.ProjectionType.CARTESIAN,
            layers=[*line_layers, ScatterLayer()],
        )
