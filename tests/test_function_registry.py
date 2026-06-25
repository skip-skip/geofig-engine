"""
Tests for the function registry system.

Covers validation, loading, registry queries, and template integration.
"""

import pytest
from geofig_engine.data import (
    FunctionType,
    FunctionCategory,
    GeospatialMetadata,
    MathFunction,
    FunctionValidator,
    FunctionLoader,
    FunctionRegistry,
    FunctionLoadError,
    get_function_registry,
)
from geofig_engine.core.layer import Layer
from geofig_engine.templates.isotope import _load_functions, isotope


class TestFunctionValidator:
    """Test FunctionValidator class."""

    def test_validate_expression_linear(self):
        """Test validation of linear expression."""
        is_valid, msg = FunctionValidator.validate_expression(
            expression="8*x + 10",
            variables=("x",),
            func_type=FunctionType.LINEAR,
        )
        assert is_valid, msg

    def test_validate_expression_missing_variable(self):
        """Test validation fails when declared variable missing from expression."""
        is_valid, msg = FunctionValidator.validate_expression(
            expression="8*x + 10",
            variables=("x", "y"),
            func_type=FunctionType.LINEAR,
        )
        assert not is_valid
        assert "not in expression" in msg

    def test_validate_expression_unexpected_variable(self):
        """Test validation fails when unexpected variable in expression."""
        is_valid, msg = FunctionValidator.validate_expression(
            expression="8*x + z",
            variables=("x",),
        )
        assert not is_valid
        assert "Unexpected" in msg

    def test_extract_variables(self):
        """Test variable extraction from expression."""
        vars = FunctionValidator.extract_variables("8*x + 10")
        assert "x" in vars
        assert len(vars) == 1

        vars = FunctionValidator.extract_variables("a*x**2 + b*x + c")
        assert {"a", "x", "b", "c"}.issubset(vars)

    def test_validate_variables_valid(self):
        """Test variable name validation."""
        is_valid, msg = FunctionValidator.validate_variables(("x", "y"))
        assert is_valid

    def test_validate_variables_invalid_identifier(self):
        """Test validation fails for invalid identifiers."""
        is_valid, msg = FunctionValidator.validate_variables(("x-y",))
        assert not is_valid

    def test_validate_variables_reserved_function(self):
        """Test validation fails when variable is reserved function name."""
        is_valid, msg = FunctionValidator.validate_variables(("sin",))
        assert not is_valid

    def test_validate_variables_duplicate(self):
        """Test validation fails for duplicate variables."""
        is_valid, msg = FunctionValidator.validate_variables(("x", "x"))
        assert not is_valid

    def test_validate_type_linear_with_exponent(self):
        """Test LINEAR type validation rejects exponents."""
        is_valid, msg = FunctionValidator._validate_type_match(
            "x**2 + 3*x + 1",
            FunctionType.LINEAR,
        )
        assert not is_valid

    def test_validate_type_exponential(self):
        """Test EXPONENTIAL type validation."""
        is_valid, msg = FunctionValidator._validate_type_match(
            "exp(x) + 5",
            FunctionType.EXPONENTIAL,
        )
        assert is_valid

    def test_validate_type_exponential_missing_exp(self):
        """Test EXPONENTIAL type validation fails without exp."""
        is_valid, msg = FunctionValidator._validate_type_match(
            "x + 5",
            FunctionType.EXPONENTIAL,
        )
        assert not is_valid


class TestMathFunction:
    """Test MathFunction dataclass."""

    def test_create_valid_function(self):
        """Test creating a valid MathFunction."""
        func = MathFunction(
            id="TEST",
            category=FunctionCategory.WATER_ISOTOPE,
            func_type=FunctionType.LINEAR,
            expression="8*x + 10",
            variables=("x",),
            color="black",
            linestyle="--",
            label="Test Line",
        )
        assert func.id == "TEST"
        assert func.category == FunctionCategory.WATER_ISOTOPE

    def test_create_function_with_geospatial(self):
        """Test creating function with geospatial metadata."""
        geo = GeospatialMetadata(
            region="Idaho",
            state="ID",
            city="Moscow",
            water_body="Palouse River",
            water_type="meteoric",
        )
        func = MathFunction(
            id="ID_MOSCOW",
            category=FunctionCategory.WATER_ISOTOPE,
            func_type=FunctionType.LINEAR,
            expression="7.5*x + 2.5",
            variables=("x",),
            color="orange",
            linestyle="-.",
            label="Moscow LMWL",
            geospatial=geo,
        )
        assert func.geospatial.state == "ID"
        assert func.geospatial.city == "Moscow"

    def test_function_validation_empty_id(self):
        """Test validation fails with empty ID."""
        with pytest.raises(ValueError):
            MathFunction(
                id="",
                category=FunctionCategory.WATER_ISOTOPE,
                func_type=FunctionType.LINEAR,
                expression="8*x + 10",
                variables=("x",),
                color="black",
                linestyle="--",
                label="Test",
            )

    def test_function_validation_empty_variables(self):
        """Test validation fails with empty variables."""
        with pytest.raises(ValueError):
            MathFunction(
                id="TEST",
                category=FunctionCategory.WATER_ISOTOPE,
                func_type=FunctionType.LINEAR,
                expression="8*x + 10",
                variables=(),
                color="black",
                linestyle="--",
                label="Test",
            )


class TestFunctionLoader:
    """Test FunctionLoader class."""

    def test_load_functions(self):
        """Test loading functions from JSON."""
        functions = FunctionLoader.load()
        assert len(functions) > 0
        assert all(isinstance(f, MathFunction) for f in functions)

    def test_load_functions_cached(self):
        """Test that functions are cached after first load."""
        # Reset cache
        FunctionLoader._cache = None

        functions1 = FunctionLoader.load()
        functions2 = FunctionLoader.load()

        # Should return same cached instance
        assert functions1 is functions2

    def test_loaded_functions_valid(self):
        """Test that loaded functions are valid."""
        functions = FunctionLoader.load()

        for func in functions:
            assert isinstance(func.id, str) and func.id
            assert isinstance(func.label, str) and func.label
            assert isinstance(func.expression, str) and func.expression
            assert isinstance(func.variables, tuple) and len(func.variables) > 0
            assert isinstance(func.color, str) and func.color
            assert isinstance(func.linestyle, str) and func.linestyle

    def test_water_isotope_functions_loaded(self):
        """Test that water isotope functions are loaded."""
        functions = FunctionLoader.load()
        water_isotope = [
            f for f in functions if f.category == FunctionCategory.WATER_ISOTOPE
        ]
        assert len(water_isotope) > 0

    def test_gmwl_loaded(self):
        """Test that GMWL is loaded."""
        functions = FunctionLoader.load()
        gmwl = [f for f in functions if f.id == "GMWL"]
        assert len(gmwl) == 1
        assert gmwl[0].label == "GMWL"
        assert gmwl[0].expression == "8*x + 10"


class TestFunctionRegistry:
    """Test FunctionRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create a registry for testing."""
        functions = FunctionLoader.load()
        return FunctionRegistry(functions)

    def test_get_by_id(self, registry):
        """Test getting function by ID."""
        func = registry.get("GMWL")
        assert func.id == "GMWL"
        assert func.label == "GMWL"

    def test_get_by_id_not_found(self, registry):
        """Test getting non-existent function raises error."""
        with pytest.raises(KeyError):
            registry.get("NONEXISTENT")

    def test_get_all(self, registry):
        """Test getting all functions."""
        all_funcs = registry.get_all()
        assert len(all_funcs) > 0

    def test_exists(self, registry):
        """Test checking if function exists."""
        assert registry.exists("GMWL")
        assert not registry.exists("NONEXISTENT")

    def test_get_by_category(self, registry):
        """Test getting functions by category."""
        water_isotope = registry.get_by_category(FunctionCategory.WATER_ISOTOPE)
        assert len(water_isotope) > 0
        assert all(f.category == FunctionCategory.WATER_ISOTOPE for f in water_isotope)

    def test_get_by_type(self, registry):
        """Test getting functions by type."""
        linear = registry.get_by_type(FunctionType.LINEAR)
        assert len(linear) > 0
        assert all(f.func_type == FunctionType.LINEAR for f in linear)

    def test_get_by_variable(self, registry):
        """Test getting functions by variable."""
        x_funcs = registry.get_by_variable("x")
        assert len(x_funcs) > 0
        assert all("x" in f.variables for f in x_funcs)

    def test_get_by_state(self, registry):
        """Test getting functions by state."""
        id_funcs = registry.get_by_state("ID")
        assert len(id_funcs) > 0
        assert all(f.geospatial.state == "ID" for f in id_funcs)

    def test_filter_by_category(self, registry):
        """Test filtering by category."""
        results = registry.filter(category=FunctionCategory.WATER_ISOTOPE)
        assert len(results) > 0

    def test_filter_by_type(self, registry):
        """Test filtering by type."""
        results = registry.filter(func_type=FunctionType.LINEAR)
        assert len(results) > 0

    def test_filter_by_category_and_type(self, registry):
        """Test filtering by both category and type."""
        results = registry.filter(
            category=FunctionCategory.WATER_ISOTOPE,
            func_type=FunctionType.LINEAR,
        )
        assert len(results) > 0
        assert all(
            f.category == FunctionCategory.WATER_ISOTOPE
            and f.func_type == FunctionType.LINEAR
            for f in results
        )

    def test_filter_by_state(self, registry):
        """Test filtering by state."""
        results = registry.filter(state="ID")
        assert len(results) > 0
        assert all(f.geospatial.state == "ID" for f in results)

    def test_list_ids(self, registry):
        """Test listing function IDs."""
        ids = registry.list_ids()
        assert len(ids) > 0
        assert "GMWL" in ids

    def test_list_ids_by_category(self, registry):
        """Test listing IDs filtered by category."""
        ids = registry.list_ids(category=FunctionCategory.WATER_ISOTOPE)
        assert len(ids) > 0

    def test_get_metadata(self, registry):
        """Test getting registry metadata."""
        metadata = registry.get_metadata()
        assert "total_functions" in metadata
        assert metadata["total_functions"] > 0
        assert "by_category" in metadata
        assert "by_type" in metadata


class TestGlobalRegistry:
    """Test the global registry singleton."""

    def test_get_function_registry(self):
        """Test getting global registry."""
        registry = get_function_registry()
        assert isinstance(registry, FunctionRegistry)

    def test_get_function_registry_singleton(self):
        """Test that global registry is a singleton."""
        registry1 = get_function_registry()
        registry2 = get_function_registry()
        assert registry1 is registry2


class TestIsotopeFactoryIntegration:
    """Test isotope factory integration with function registry."""

    def test_load_functions_empty(self):
        layers = _load_functions(functions=[])
        assert len(layers) == 0

    def test_load_functions_auto_filter(self):
        layers = _load_functions(auto_filter=True)
        assert len(layers) >= 1
        assert all(isinstance(l, Layer) for l in layers)

    def test_load_functions_specific(self):
        layers = _load_functions(functions=["GMWL", "ID_FALLS"])
        assert len(layers) == 2

    def test_load_functions_invalid_id(self):
        with pytest.raises(KeyError, match="not found in registry"):
            _load_functions(functions=["NONEXISTENT"])

    def test_isotope_factory_uses_load_functions(self):
        template = isotope(auto_filter=True)
        assert len(template.layers) >= 2
