"""
Function registry and loader (legacy API).

DEPRECATED as a data source: the underlying catalog now lives in the
geom_presets package (data/geom_presets/*.json). This module adapts
function_line-type presets into legacy MathFunction views so existing
call sites keep working. New code should use
geofig_engine.data.geom_presets.get_geom_preset_registry() directly.
"""

from geofig_engine.data.functions import (
    FunctionType,
    FunctionCategory,
    MathFunction,
    GeospatialMetadata,
)
from geofig_engine.data.validator import FunctionValidator
from geofig_engine.data.geom_presets.models import GeomPreset
from geofig_engine.data.geom_presets.registry import get_geom_preset_registry


class FunctionLoadError(Exception):
    """Raised when function loading or validation fails."""

    pass


class FunctionLoader:
    """Load functions from the geom preset registry (legacy view)."""

    _cache: list[MathFunction] | None = None

    @classmethod
    def load(cls) -> list[MathFunction]:
        """
        Load all function-line presets as legacy MathFunction instances.

        Presets whose items are not exclusively function_line geoms are
        skipped (they have no MathFunction representation).

        Returns:
            List of validated MathFunction instances

        Raises:
            FunctionLoadError: If preset loading or conversion fails
        """
        if cls._cache is not None:
            return cls._cache

        try:
            presets = get_geom_preset_registry().get_all()

            functions: list[MathFunction] = []
            for preset in presets:
                if preset.geom_kinds != {"function_line"} or len(preset.items) != 1:
                    continue
                try:
                    functions.append(cls._preset_to_function(preset))
                except Exception as e:
                    raise FunctionLoadError(
                        f"Failed to adapt preset '{preset.id}' to MathFunction: {e}"
                    ) from e

            cls._cache = functions
            return functions

        except FunctionLoadError:
            raise
        except Exception as e:
            raise FunctionLoadError(f"Failed to load functions: {e}")

    @staticmethod
    def _preset_to_function(preset: GeomPreset) -> MathFunction:
        """
        Convert a single-item function_line preset into a MathFunction.

        Args:
            preset: GeomPreset with exactly one function_line item

        Returns:
            MathFunction instance
        """
        item = preset.items[0]
        expression = item.params["func"]

        extracted = FunctionValidator.extract_variables(expression) - {"pi", "e"}
        variables = tuple(sorted(extracted)) if extracted else ("x",)

        func_type_str = item.func_type or "linear"

        return MathFunction(
            id=preset.id,
            category=FunctionCategory(preset.category),
            func_type=FunctionType(func_type_str),
            expression=expression,
            variables=variables,
            color=item.mapping["color"],
            linestyle=item.mapping["style"],
            label=item.mapping["label"],
            reference=preset.reference,
            description=preset.description,
            valid_domain=preset.valid_domain,
            geospatial=GeospatialMetadata(
                region=preset.geospatial.get("region"),
                state=preset.geospatial.get("state"),
                city=preset.geospatial.get("city"),
                water_body=preset.geospatial.get("water_body"),
                water_type=preset.geospatial.get("water_type"),
            ),
        )


class FunctionRegistry:
    """Query and manage the function database."""

    def __init__(self, functions: list[MathFunction]):
        """
        Initialize registry with functions.

        Args:
            functions: List of MathFunction instances
        """
        self._functions = functions
        self._by_id = {f.id: f for f in functions}
        self._by_category = self._index_by_field("category")
        self._by_type = self._index_by_field("func_type")
        self._by_variable = self._index_by_variable()

    def get(self, func_id: str) -> MathFunction:
        """
        Get function by ID.

        Args:
            func_id: Function ID

        Returns:
            MathFunction instance

        Raises:
            KeyError: If function not found
        """
        if func_id not in self._by_id:
            raise KeyError(f"Function '{func_id}' not found in registry")
        return self._by_id[func_id]

    def get_all(self) -> list[MathFunction]:
        """
        Get all functions.

        Returns:
            List of all MathFunction instances
        """
        return list(self._functions)

    def exists(self, func_id: str) -> bool:
        """
        Check if function exists by ID.

        Args:
            func_id: Function ID

        Returns:
            True if function exists
        """
        return func_id in self._by_id

    def get_by_category(self, category: FunctionCategory) -> list[MathFunction]:
        """
        Get all functions in a category.

        Args:
            category: FunctionCategory enum value

        Returns:
            List of MathFunction instances
        """
        return self._by_category.get(category, [])

    def get_by_type(self, func_type: FunctionType) -> list[MathFunction]:
        """
        Get all functions of a type.

        Args:
            func_type: FunctionType enum value

        Returns:
            List of MathFunction instances
        """
        return self._by_type.get(func_type, [])

    def get_by_variable(self, variable_name: str) -> list[MathFunction]:
        """
        Get all functions using a specific variable.

        Args:
            variable_name: Variable name (e.g., "x")

        Returns:
            List of MathFunction instances
        """
        return self._by_variable.get(variable_name, [])

    def get_by_state(self, state_code: str) -> list[MathFunction]:
        """
        Get all functions associated with a state.

        Args:
            state_code: State code (e.g., "ID", "WA")

        Returns:
            List of MathFunction instances
        """
        return [f for f in self._functions if f.geospatial.state == state_code]

    def filter(
        self,
        category: FunctionCategory | None = None,
        func_type: FunctionType | None = None,
        variables: tuple[str, ...] | None = None,
        require_all_variables: bool = False,
        state: str | None = None,
    ) -> list[MathFunction]:
        """
        Advanced filtering.

        Args:
            category: Filter by category
            func_type: Filter by function type
            variables: Filter by required variables
            require_all_variables: If True, function must have ALL variables.
                                  If False, function must have ANY of them.
            state: Filter by state code

        Returns:
            Filtered list of MathFunction instances
        """
        results = self._functions

        if category is not None:
            results = [f for f in results if f.category == category]

        if func_type is not None:
            results = [f for f in results if f.func_type == func_type]

        if variables is not None:
            var_set = set(variables)
            if require_all_variables:
                results = [
                    f for f in results
                    if var_set.issubset(set(f.variables))
                ]
            else:
                results = [
                    f for f in results
                    if var_set & set(f.variables)
                ]

        if state is not None:
            results = [f for f in results if f.geospatial.state == state]

        return results

    def list_ids(
        self,
        category: FunctionCategory | None = None,
        func_type: FunctionType | None = None,
    ) -> list[str]:
        """
        List function IDs with optional filters.

        Args:
            category: Optional category filter
            func_type: Optional function type filter

        Returns:
            List of function IDs
        """
        results = self.filter(category=category, func_type=func_type)
        return [f.id for f in results]

    def get_metadata(self) -> dict:
        """
        Get registry statistics and metadata.

        Returns:
            Dictionary with counts and information
        """
        by_category = {}
        by_type = {}
        by_state = {}

        for func in self._functions:
            # Count by category
            cat_name = func.category.value
            by_category[cat_name] = by_category.get(cat_name, 0) + 1

            # Count by type
            type_name = func.func_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

            # Count by state
            if func.geospatial.state:
                state = func.geospatial.state
                by_state[state] = by_state.get(state, 0) + 1

        return {
            "total_functions": len(self._functions),
            "by_category": by_category,
            "by_type": by_type,
            "by_state": by_state,
        }

    def _index_by_field(self, field_name: str) -> dict:
        """Create index by a field value."""
        index = {}
        for func in self._functions:
            field_value = getattr(func, field_name)
            if field_value not in index:
                index[field_value] = []
            index[field_value].append(func)
        return index

    def _index_by_variable(self) -> dict:
        """Create index by variable names."""
        index = {}
        for func in self._functions:
            for var in func.variables:
                if var not in index:
                    index[var] = []
                index[var].append(func)
        return index


# Global registry instance (lazy-loaded)
_REGISTRY: FunctionRegistry | None = None


def get_function_registry() -> FunctionRegistry:
    """
    Get or create the global function registry (lazy-loaded).

    Legacy view over the geom preset catalog.

    Returns:
        FunctionRegistry instance

    Raises:
        FunctionLoadError: If loading fails
    """
    global _REGISTRY
    if _REGISTRY is None:
        functions = FunctionLoader.load()
        _REGISTRY = FunctionRegistry(functions)
    return _REGISTRY
