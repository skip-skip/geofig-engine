import enum
from typing import Any

from geofig_engine.core.dataset import Dataset
from geofig_engine.core.iterator import DimensionIterator

from geofig_cli.selectors import get_dimension_names, get_label_keys, get_selector_options
from geofig_cli.state import ConfigState, IteratorConfig, MappingValue, LayerOption
from geofig_cli.ui import choose_grouped_horizontal, choose_horizontal, confirm, text_input

def add_iterator(stdscr, dataset: Dataset, state: ConfigState) -> None:
    # ---------------------------------------------------
    # iterator channel name
    # ---------------------------------------------------
    channel = text_input(
        stdscr,
        "Add Iterator",
        "Channel name",
    )

    if not channel:
        return

    # ---------------------------------------------------
    # selector selection
    # ---------------------------------------------------
    selector_sections = [
        (
            "Dimensions",
            get_dimension_names(dataset),
        ),
        (
            "Labels",
            get_label_keys(dataset),
        ),
        (
            "Manual",
            ["<manual>"],
        ),
    ]

    selector_result = choose_grouped_horizontal(
        stdscr,
        "Select iterator selector",
        selector_sections,
    )

    if selector_result is None:
        return

    selector_section, selector_value = selector_result

    # manual selector input
    if selector_section == "Manual":
        selector = text_input(
            stdscr,
            "Manual Selector",
            "Selector",
        )

        if not selector:
            return
    else:
        selector = selector_value

    # ---------------------------------------------------
    # iterator mode selection
    # ---------------------------------------------------
    mode_sections = [
        (
            "Iterator Modes",
            [
                DimensionIterator.Mode.DIMENSION.name,
                DimensionIterator.Mode.VALUE.name,
            ],
        )
    ]

    mode_result = choose_grouped_horizontal(
        stdscr,
        "Select iterator mode",
        mode_sections,
    )

    if mode_result is None:
        return

    _, mode_name = mode_result

    # ---------------------------------------------------
    # save iterator
    # ---------------------------------------------------
    state.iterators.append(
        IteratorConfig(
            channel=channel,
            selector=selector,
            mode=DimensionIterator.Mode[mode_name],
        )
    )

def edit_iterator(stdscr, state: ConfigState, iterator: IteratorConfig) -> None:
    delete = confirm(
        stdscr,
        "Iterator",
        f"Delete iterator {{{iterator.channel}}}?",
    )

    if delete:
        state.iterators = [
            item for item in state.iterators
            if item is not iterator
        ]

def edit_mapping(
    stdscr,
    dataset: Dataset,
    state: ConfigState,
    mapping_key: str,
    required: bool = False,
) -> None:

    sections = [
        (
            "Dimensions",
            get_dimension_names(dataset),
        ),
        (
            "Labels",
            get_label_keys(dataset),
        ),
        (
            "Iterators",
            [i.channel for i in state.iterators],
        ),
    ]

    if not required:
        sections.append(
            (
                "Single Value",
                ["<manual>"],
            )
        )

    result = choose_grouped_horizontal(
        stdscr,
        f"Mapping: {mapping_key}",
        sections,
    )
    if result is None:
        return
    section_name, value = result

    # -------------------------
    # manual entry
    # -------------------------
    value_resolved = ''
    if section_name == "Single Value":
        value = text_input(
            stdscr,
            f"Mapping to single value: {mapping_key}",
            "Value",
        )
        if value is None:
            return
        mapping_type = "value"
        value_resolved = value
    elif section_name == "Dimensions":
        mapping_type = "dimension"
        value_resolved = [value]
    elif section_name == "Labels":
        mapping_type = "label"
        value_resolved = dataset.query_dimensions(value, True)
    else:
        mapping_type = "iterator"
        value_resolved = f"{'{'}{value}{'}'}"

    state.mappings[mapping_key] = MappingValue(
        mapping_type=mapping_type,
        value=value,
        value_resolved=value_resolved
    )

def is_enum_value(value: Any) -> bool:
    return isinstance(value, enum.Enum)


def edit_setting_value(stdscr, title: str, current_value: Any) -> Any | None:
    if is_enum_value(current_value):
        enum_cls = type(current_value)

        selected = choose_horizontal(
            stdscr,
            title,
            [item.name for item in enum_cls],
            allow_manual=False,
            default=current_value.name,
        )

        if not selected:
            return None

        return enum_cls[selected]

    return text_input(
        stdscr,
        title,
        "Value",
        default=str(current_value),
    )


def edit_setting(stdscr, state: ConfigState, setting_key: str) -> None:
    value = edit_setting_value(
        stdscr,
        f"Setting: {setting_key}",
        state.settings.get(setting_key),
    )

    if value is not None:
        state.settings[setting_key] = value


def edit_layer_setting(stdscr, state: ConfigState, setting_key: str) -> None:
    value = edit_setting_value(
        stdscr,
        f"Layer Setting: {setting_key}",
        state.layer_settings.get(setting_key),
    )

    if value is not None:
        state.layer_settings[setting_key] = value
        
def toggle_layer_option(option: LayerOption) -> None:
    option.selected = not option.selected