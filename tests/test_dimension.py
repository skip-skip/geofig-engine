from geofig_engine.core.dimension import Dimension


def test_dimension_stores_name_and_attributes() -> None:
    dimension = Dimension(name="chem1", attributes={"analyte": True, "unit": "mg/L"})

    assert dimension.name == "chem1"
    assert dimension.attributes["analyte"] is True
    assert dimension.attributes["unit"] == "mg/L"


def test_get_attribute_returns_value_or_default() -> None:
    dimension = Dimension(name="group", attributes={"role": "group"})

    assert dimension.get_attribute("role") == "group"
    assert dimension.get_attribute("missing", default="none") == "none"


def test_has_attribute_checks_metadata_key() -> None:
    dimension = Dimension(name="id", attributes={"role": "key"})

    assert dimension.has_attribute("role") is True
    assert dimension.has_attribute("unit") is False


def test_is_role_matches_value() -> None:
    dimension = Dimension(name="group", attributes={"role": "group"})

    assert dimension.is_role("group") is True
    assert dimension.is_role("analyte") is False


def test_invalid_attribute_keys_raise_type_error() -> None:
    try:
        Dimension(name="chem1", attributes={1: "bad"})
        assert False, "Expected TypeError for non-string attribute key"
    except TypeError:
        pass
