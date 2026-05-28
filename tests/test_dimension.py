from geofig_engine.core.dimension import Dimension


def test_dimension_stores_name_and_attributes() -> None:
    dimension = Dimension(name="chem1", labels={"analyte": True, "unit": "mg/L"})

    assert dimension.name == "chem1"
    assert dimension.labels["analyte"] is True
    assert dimension.labels["unit"] == "mg/L"


def test_get_attribute_returns_value_or_default() -> None:
    dimension = Dimension(name="group", labels={"role": "group"})

    assert dimension.get_label("role") == "group"
    assert dimension.get_label("missing", default="none") == "none"


def test_has_attribute_checks_metadata_key() -> None:
    dimension = Dimension(name="id", labels={"role": "key"})

    assert dimension.has_label("role") is True
    assert dimension.has_label("unit") is False

def test_invalid_attribute_keys_raise_type_error() -> None:
    try:
        Dimension(name="chem1", labels={1: "bad"})
        assert False, "Expected TypeError for non-string attribute key"
    except TypeError:
        pass
