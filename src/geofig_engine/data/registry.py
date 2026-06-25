"""
Function registry and loader.

Loads mathematical functions from JSON, validates them,
and provides querying and filtering capabilities.
"""

import json
from pathlib import Path
from typing import ClassVar

from geofig_engine.data.functions import (
    FunctionType,
    FunctionCategory,
    MathFunction,
    GeospatialMetadata,
)
from geofig_engine.data.validator import FunctionValidator


class FunctionLoadError(Exception):
    """Raised when function JSON loading or validation fails."""

    pass


class FunctionLoader:
    """Load and validate functions from JSON file."""

    _cache: ClassVar[list[MathFunction] | None] = None

    @classmethod
    def load(cls) -> list[MathFunction]:
        """
        Load all functions from JSON file.

        Returns:
            List of validated MathFunction instances

        Raises:
            FunctionLoadError: If loading or validation fails
        """
        if cls._cache is not None:
            return cls._cache

        try:
            json_data = cls._load_json()
            cls._validate_schema(json_data)

            functions = []
            for idx, item in enumerate(json_data.get("functions", [])):
                try:
                    func = cls._hydrate_function(item)
                    functions.append(func)
                except Exception as e:
                    raise FunctionLoadError(
                        f"Failed to load function at index {idx} "
                        f"(id: {item.get('id', 'unknown')}): {str(e)}"
                    )

            cls._cache = functions
            return functions

        except FunctionLoadError:
            raise
        except Exception as e:
            raise FunctionLoadError(f"Failed to load functions: {str(e)}")

    @classmethod
    def _load_json(cls) -> dict:
        """
        Load JSON file from disk.

        Returns:
            Parsed JSON data

        Raises:
            FunctionLoadError: If file not found or JSON invalid
        """
        json_path = cls._get_json_path()

        if not json_path.exists():
            raise FunctionLoadError(f"Functions JSON file not found: {json_path}")

        try:
            with open(json_path, encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise FunctionLoadError(f"Invalid JSON in {json_path}: {str(e)}")

    @classmethod
    def _get_json_path(cls) -> Path:
        """
        Get path to functions.json file.

        Returns:
            Path to functions.json relative to this module
        """
        # functions.json is in the same directory as this module
        module_dir = Path(__file__).parent
        return module_dir / "functions.json"

    @classmethod
    def _validate_schema(cls, data: dict) -> None:
        """
        Validate JSON schema structure.

        Args:
            data: Parsed JSON data

        Raises:
            FunctionLoadError: If schema is invalid
        """
        if not isinstance(data, dict):
            raise FunctionLoadError("Root element must be a dictionary")

        if "functions" not in data:
            raise FunctionLoadError("Missing 'functions' key in root")

        if not isinstance(data["functions"], list):
            raise FunctionLoadError("'functions' must be an array")

        required_keys = {"id", "category", "type", "expression", "variables", "color", "linestyle", "label"}
        for idx, item in enumerate(data["functions"]):
            if not isinstance(item, dict):
                raise FunctionLoadError(f"Function at index {idx} is not a dictionary")

            missing = required_keys - set(item.keys())
            if missing:
                raise FunctionLoadError(
                    f"Function at index {idx} missing required keys: {missing}"
                )

    @classmethod
    def _hydrate_function(cls, item: dict) -> MathFunction:
        """
        Convert JSON item to MathFunction instance with validation.

        Args:
            item: Dictionary from JSON

        Returns:
            Validated MathFunction instance

        Raises:
            FunctionLoadError: If validation fails
        """
        # Validate expression
        variables_list = item.get("variables", [])
        if not isinstance(variables_list, list):
            raise ValueError("'variables' must be a list")

        variables = tuple(variables_list)

        is_valid, error = FunctionValidator.validate_expression(
            expression=item["expression"],
            variables=variables,
            func_type=FunctionType(item["type"]),
        )
        if not is_valid:
            raise ValueError(f"Invalid expression: {error}")

        # Validate variables
        is_valid, error = FunctionValidator.validate_variables(variables)
        if not is_valid:
            raise ValueError(f"Invalid variables: {error}")

        # Build geospatial metadata
        geo_data = item.get("geospatial", {})
        if not isinstance(geo_data, dict):
            geo_data = {}

        geospatial = GeospatialMetadata(
            region=geo_data.get("region"),
            state=geo_data.get("state"),
            city=geo_data.get("city"),
            water_body=geo_data.get("water_body"),
            water_type=geo_data.get("water_type"),
        )

        # Create MathFunction
        return MathFunction(
            id=item["id"],
            category=FunctionCategory(item["category"]),
            func_type=FunctionType(item["type"]),
            expression=item["expression"],
            variables=variables,
            color=item["color"],
            linestyle=item["linestyle"],
            label=item["label"],
            reference=item.get("reference"),
            description=item.get("description"),
            valid_domain=item.get("valid_domain"),
            geospatial=geospatial,
            custom_metadata=item.get("custom_metadata", {}),
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
