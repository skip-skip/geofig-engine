import curses
from pathlib import Path
from typing import Any

from geofig_cli.data import load_dataset
from geofig_cli.editors import add_iterator, edit_iterator, edit_layer_setting, edit_mapping, edit_setting, toggle_layer_option
#from cli.main import ESCAPE, Cell, ConfigState, build_cells, choose_option, edit_iterator, initialize_config_state, load_dataset, message, prompt, render_figures
from geofig_cli.registry import TEMPLATE_REGISTRY
from geofig_cli.rendering import render_figures
from geofig_cli.state import Cell, ConfigState
from geofig_cli.table import build_cells, initialize_config_state
from geofig_cli.ui import ENTER_KEYS, ESCAPE, choose_vertical, choose_vertical_multi, draw_footer, message, prompt, truncate
from geofig_cli.ui import choose_option
from geofig_engine.core.dataset import Dataset



def run_cli() -> None:
    print("\n=== FigEngine CLI ===\n")

    input_path = Path(prompt("Input file path (xlsx/csv)"))

    dataset = load_dataset(input_path)

    result = curses.wrapper(run_curses_app, dataset)

    if result == "exit":
        print("\nExiting FigEngine CLI.\n")

def run_curses_app(stdscr, dataset: Dataset) -> str:
    while True:
        template = select_template(stdscr)

        if template is None:
            return "exit"

        state = initialize_config_state(template)
        result = configuration_table(stdscr,dataset,template,state,)
        
        if result == "exit":
            return "exit"
        if result == "back":
            continue
        
def select_template(stdscr) -> Any | None:
    while True:
        template_names = list(TEMPLATE_REGISTRY.keys())

        name = choose_vertical(
            stdscr,
            "Available templates",
            template_names,
            allow_escape=True,
        )

        if name is None:
            return None

        template_cls = TEMPLATE_REGISTRY[name]
        return template_cls()
    
def configuration_table(stdscr, dataset: Dataset, template: Any, state: ConfigState) -> str:
    curses.curs_set(0)
    stdscr.keypad(True)

    selected_row = 0
    selected_col = 0
    command_buffer = ""

    while True:
        rows = draw_config_table(
            stdscr,
            template,
            state,
            selected_row,
            selected_col,
            command_buffer,
        )

        if not rows:
            message(stdscr, "No configurable fields are available.")
            return "back"

        key = stdscr.getch()

        if key == ESCAPE:
            return "back"

        if key == curses.KEY_UP:
            selected_row, selected_col = move_to_valid_cell(
                rows,
                selected_row,
                selected_col,
                row_delta=-1,
            )

        elif key == curses.KEY_DOWN:
            selected_row, selected_col = move_to_valid_cell(
                rows,
                selected_row,
                selected_col,
                row_delta=1,
            )

        elif key == curses.KEY_LEFT:
            selected_row, selected_col = move_to_valid_cell(
                rows,
                selected_row,
                selected_col,
                col_delta=-1,
            )

        elif key == curses.KEY_RIGHT:
            selected_row, selected_col = move_to_valid_cell(
                rows,
                selected_row,
                selected_col,
                col_delta=1,
            )

        elif key in ENTER_KEYS:
            command = command_buffer.strip().lower()
            command_buffer = ""

            if command == "render":
                render_figures(stdscr, dataset, template, state)

            elif command == "back":
                return "back"

            elif command == "exit":
                return "exit"

            elif command:
                message(stdscr, f"Unknown command: {command}")

            else:
                cell = rows[selected_row][selected_col]
                run_cell_action(stdscr, dataset, template, state, cell)

        elif key in {curses.KEY_BACKSPACE, 127, 8}:
            command_buffer = command_buffer[:-1]

        elif 32 <= key <= 126:
            command_buffer += chr(key)
def draw_config_table(
    stdscr,
    template: Any,
    state: ConfigState,
    selected_row: int,
    selected_col: int,
    command_buffer: str,
) -> list[list[Cell]]:
    stdscr.clear()

    height, width = stdscr.getmaxyx()
    rows = build_cells(template, state)

    headers = ["Iterators", "Mappings", "Settings", "Layer Settings"]
    col_width = max(18, width // len(headers) - 2)

    stdscr.addstr(0, 2, "Configuration", curses.A_BOLD)
    stdscr.addstr(1, 2, "Select a cell to edit. Type render, back, or exit.", curses.A_DIM)

    y = 3
    x = 0

    for col_idx, header in enumerate(headers):
        stdscr.addstr(y, x + 1, truncate(header, col_width - 2), curses.A_BOLD)
        x += col_width

    y += 1

    visible_rows = max(1, height - 7)

    if selected_row >= visible_rows:
        start_row = selected_row - visible_rows + 1
    else:
        start_row = 0

    end_row = min(len(rows), start_row + visible_rows)

    for table_row_idx in range(start_row, end_row):
        row = rows[table_row_idx]
        x = 0

        for col_idx, cell in enumerate(row):
            selected = (
                table_row_idx == selected_row
                and col_idx == selected_col
                and cell.action != "empty"
            )

            attr = curses.A_REVERSE if selected else curses.A_NORMAL
            display = truncate(cell.display, col_width - 2)

            stdscr.addstr(y, x, " " * (col_width - 1), attr)
            stdscr.addstr(y, x + 1, display, attr)

            x += col_width

        y += 1

    draw_footer(stdscr, command_buffer)

    stdscr.refresh()

    return rows


def move_to_valid_cell(
    rows: list[list[Cell]],
    row: int,
    col: int,
    row_delta: int = 0,
    col_delta: int = 0,
) -> tuple[int, int]:
    if not rows:
        return 0, 0

    max_row = len(rows) - 1
    max_col = len(rows[0]) - 1

    new_row = min(max(row + row_delta, 0), max_row)
    new_col = min(max(col + col_delta, 0), max_col)

    if rows[new_row][new_col].action != "empty":
        return new_row, new_col

    # Try to find nearest valid cell in the intended direction.
    candidates: list[tuple[int, int]] = []

    if row_delta != 0:
        step = 1 if row_delta > 0 else -1
        for r in range(new_row, max_row + 1 if step > 0 else -1, step):
            if rows[r][new_col].action != "empty":
                candidates.append((r, new_col))
                break

    if col_delta != 0:
        step = 1 if col_delta > 0 else -1
        for c in range(new_col, max_col + 1 if step > 0 else -1, step):
            if rows[new_row][c].action != "empty":
                candidates.append((new_row, c))
                break

    if candidates:
        return candidates[0]

    return row, col


def run_cell_action(
    stdscr,
    dataset: Dataset,
    template: Any,
    state: ConfigState,
    cell: Cell,
) -> None:
    if cell.action == "add_iterator":
        add_iterator(stdscr, dataset, state)

    elif cell.action == "edit_iterator":
        edit_iterator(stdscr, state, cell.payload)

    elif cell.action == "edit_mapping":
        edit_mapping(stdscr, dataset, state, cell.payload)

    elif cell.action == "edit_setting":
        edit_setting(stdscr, state, cell.payload)

    elif cell.action == "edit_layer_setting":
        edit_layer_setting(stdscr, state, cell.payload)

    elif cell.action == "toggle_layer_option":
        toggle_layer_option(cell.payload)