from typing import Any

from geofig_cli.state import Cell, ConfigState, LayerOption
from geofig_engine.data import get_function_registry, FunctionCategory, FunctionType


def get_supported_mappings(template: Any) -> list[str]:
    return []

def get_default_settings(template: Any) -> dict[str, Any]:
    return dict(getattr(template, "default_settings", {}))

def get_default_layer_settings(template: Any) -> dict[str, Any]:
    return {}

def initialize_config_state(template: Any) -> ConfigState:

    return ConfigState(
        iterators=[],
        mappings={},
        settings=get_default_settings(template),
        layer_settings=get_default_layer_settings(template),
        layer_options=get_template_layer_options(template),
    )


def build_cells(template: Any, state: ConfigState) -> list[list[Cell]]:
    iterator_cells: list[Cell] = []

    for iterator in state.iterators:
        iterator_cells.append(
            Cell(
                group="Iterators",
                key=iterator.channel,
                display=f"{{{iterator.channel}}}",
                action="edit_iterator",
                payload=iterator,
            )
        )

    iterator_cells.append(
        Cell(
            group="Iterators",
            key="+",
            display="+",
            action="add_iterator",
        )
    )

    mapping_cells = [
        Cell(
            group="Mappings",
            key=key,
            display=(
                f"{key}: {state.mappings[key].render()}"
                if key in state.mappings
                else f"{key}: [Default]"
            ),
            action="edit_mapping",
            payload=key,
        )
        for key in get_supported_mappings(template)
    ]

    setting_cells = [
        Cell(
            group="Settings",
            key=key,
            display=f"{key}: {value}",
            action="edit_setting",
            payload=key,
        )
        for key, value in state.settings.items()
    ]

    layer_setting_cells = []

    for option in state.layer_options:
        marker = "[x]" if option.selected else "[ ]"

        layer_setting_cells.append(
            Cell(
                group="Layer Settings",
                key=option.display_name(),
                display=f"{marker} {option.display_name()}",
                action="toggle_layer_option",
                payload=option,
            )
        )

    # Optional: keep any non-enum layer settings below the toggleable options.
    for key, value in state.layer_settings.items():
        layer_setting_cells.append(
            Cell(
                group="Layer Settings",
                key=key,
                display=f"{key}: {value}",
                action="edit_layer_setting",
                payload=key,
            )
        )

    columns = [
        iterator_cells,
        mapping_cells,
        setting_cells,
        layer_setting_cells,
    ]

    max_rows = max(len(col) for col in columns) if columns else 0
    rows: list[list[Cell]] = []

    for row_idx in range(max_rows):
        row: list[Cell] = []

        for col in columns:
            if row_idx < len(col):
                row.append(col[row_idx])
            else:
                row.append(
                    Cell(
                        group="",
                        key="",
                        display="",
                        action="empty",
                    )
                )

        rows.append(row)

    return rows


def get_template_layer_options(template: Any) -> list[LayerOption]:
    return []