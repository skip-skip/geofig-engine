import curses

ESCAPE = 27
ENTER_KEYS = {curses.KEY_ENTER, 10, 13}
SPACE_KEYS = {32}

def draw_footer(stdscr, command_buffer: str = "") -> None:
    height, width = stdscr.getmaxyx()

    footer = (
        "Arrows: move | Enter: edit/select | Esc: back | "
        "Commands: render, back, exit"
    )

    stdscr.addstr(height - 2, 0, footer[: width - 1], curses.A_DIM)

    command = f"> {command_buffer}"
    stdscr.addstr(height - 1, 0, command[: width - 1], curses.A_BOLD)


def center_text(stdscr, y: int, text: str, attr: int = 0) -> None:
    _, width = stdscr.getmaxyx()
    x = max(0, (width - len(text)) // 2)
    stdscr.addstr(y, x, text, attr)


def message(stdscr, text: str) -> None:
    stdscr.clear()
    center_text(stdscr, 2, text, curses.A_BOLD)
    center_text(stdscr, 4, "Press any key to continue.")
    stdscr.refresh()
    stdscr.getch()


def truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text

    if width <= 3:
        return text[:width]

    return text[: width - 3] + "..."


def text_input(stdscr, title: str, prompt_text: str, default: str = "") -> str | None:
    curses.curs_set(1)

    value = default
    cursor = len(value)

    while True:
        stdscr.clear()
        stdscr.addstr(1, 2, title, curses.A_BOLD)
        stdscr.addstr(3, 2, prompt_text)
        stdscr.addstr(5, 2, value)

        stdscr.move(5, 2 + cursor)
        stdscr.refresh()

        key = stdscr.getch()

        if key == ESCAPE:
            curses.curs_set(0)
            return None

        if key in ENTER_KEYS:
            curses.curs_set(0)
            return value.strip()

        if key in {curses.KEY_BACKSPACE, 127, 8}:
            if cursor > 0:
                value = value[: cursor - 1] + value[cursor:]
                cursor -= 1

        elif key == curses.KEY_LEFT:
            cursor = max(0, cursor - 1)

        elif key == curses.KEY_RIGHT:
            cursor = min(len(value), cursor + 1)

        elif 32 <= key <= 126:
            ch = chr(key)
            value = value[:cursor] + ch + value[cursor:]
            cursor += 1


def confirm(stdscr, title: str, prompt_text: str) -> bool | None:
    options = ["No", "Yes"]
    idx = 0

    while True:
        stdscr.clear()
        stdscr.addstr(1, 2, title, curses.A_BOLD)
        stdscr.addstr(3, 2, prompt_text)

        x = 2
        for i, option in enumerate(options):
            attr = curses.A_REVERSE if i == idx else curses.A_NORMAL
            stdscr.addstr(5, x, f" {option} ", attr)
            x += len(option) + 4

        stdscr.refresh()
        key = stdscr.getch()

        if key == ESCAPE:
            return None

        if key == curses.KEY_LEFT:
            idx = max(0, idx - 1)

        elif key == curses.KEY_RIGHT:
            idx = min(len(options) - 1, idx + 1)

        elif key in ENTER_KEYS:
            return options[idx] == "Yes"

def safe_addstr(stdscr, y: int, x: int, text: str, attr: int = curses.A_NORMAL) -> None:
    height, width = stdscr.getmaxyx()

    if y < 0 or y >= height:
        return

    if x < 0 or x >= width:
        return

    available = width - x - 1

    if available <= 0:
        return

    clipped = str(text)[:available]

    if clipped:
        try:
            stdscr.addstr(y, x, clipped, attr)
        except curses.error:
            pass

def visible_item_window(
    items: list[str],
    selected_idx: int,
    max_width: int,
    padding: int = 4,
) -> tuple[int, int]:
    """
    Return start and end indices for a horizontal item window
    that keeps the selected item visible.
    """
    if not items:
        return 0, 0

    start = selected_idx
    used = 0

    # Walk backward to include as many prior items as fit.
    while start > 0:
        candidate_len = len(str(items[start - 1])) + padding

        if used + candidate_len > max_width // 2:
            break

        used += candidate_len
        start -= 1

    end = start
    used = 0

    while end < len(items):
        item_len = len(str(items[end])) + padding

        if used + item_len > max_width:
            break

        used += item_len
        end += 1

    # If the selected item did not fit, force it in.
    if selected_idx >= end:
        start = selected_idx
        end = selected_idx + 1

    return start, end

def choose_grouped_horizontal(
    stdscr,
    title: str,
    sections: list[tuple[str, list[str]]],
):
    curses.curs_set(0)

    sections = [
        (header, items)
        for header, items in sections
        if items
    ]

    if not sections:
        return None

    section_idx = 0
    item_idx = 0

    while True:
        stdscr.clear()

        height, width = stdscr.getmaxyx()

        safe_addstr(stdscr, 1, 2, title, curses.A_BOLD)

        y = 3

        for s_idx, (header, items) in enumerate(sections):
            if y >= height - 3:
                break

            header_attr = curses.A_BOLD
            if s_idx == section_idx:
                header_attr |= curses.A_UNDERLINE

            safe_addstr(stdscr, y, 2, header, header_attr)

            y += 1

            if y >= height - 3:
                break

            selected_for_section = item_idx if s_idx == section_idx else 0
            selected_for_section = min(selected_for_section, len(items) - 1)

            max_item_width = max(10, width - 8)
            start, end = visible_item_window(
                items,
                selected_for_section,
                max_item_width,
            )

            x = 4

            if start > 0:
                safe_addstr(stdscr, y, x, "<", curses.A_DIM)
                x += 3

            for i_idx in range(start, end):
                item = str(items[i_idx])

                attr = curses.A_NORMAL

                if s_idx == section_idx and i_idx == item_idx:
                    attr = curses.A_REVERSE

                if x >= width - 2:
                    break

                safe_addstr(stdscr, y, x, item, attr)

                x += len(item) + 4

            if end < len(items) and x < width - 2:
                safe_addstr(stdscr, y, x, ">", curses.A_DIM)

            y += 2

        safe_addstr(
            stdscr,
            height - 2,
            2,
            "Left/Right: item | Up/Down: group | Enter: select | Esc: back",
            curses.A_DIM,
        )

        stdscr.refresh()

        key = stdscr.getch()

        current_items = sections[section_idx][1]

        if key == curses.KEY_RIGHT:
            item_idx = min(item_idx + 1, len(current_items) - 1)

        elif key == curses.KEY_LEFT:
            item_idx = max(item_idx - 1, 0)

        elif key == curses.KEY_DOWN:
            section_idx = min(section_idx + 1, len(sections) - 1)
            item_idx = min(item_idx, len(sections[section_idx][1]) - 1)

        elif key == curses.KEY_UP:
            section_idx = max(section_idx - 1, 0)
            item_idx = min(item_idx, len(sections[section_idx][1]) - 1)

        elif key in ENTER_KEYS:
            return (
                sections[section_idx][0],
                sections[section_idx][1][item_idx],
            )

        elif key == ESCAPE:
            return None        
def choose_horizontal(
    stdscr,
    title: str,
    options: list[str],
    allow_manual: bool = False,
    default: str | None = None,
    max_visible: int = 6,
) -> str | None:
    if not options and not allow_manual:
        message(stdscr, "No options are available.")
        return None

    idx = 0
    typed = ""

    if default and default in options:
        idx = options.index(default)

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        stdscr.addstr(1, 2, title, curses.A_BOLD)

        if options:
            start = max(0, idx - max_visible // 2)
            end = min(len(options), start + max_visible)
            visible = options[start:end]

            x = 2
            y = 4

            if start > 0:
                stdscr.addstr(y, x, "< ")
                x += 2

            for offset, option in enumerate(visible):
                actual_idx = start + offset
                label = truncate(option, 24)
                attr = curses.A_REVERSE if actual_idx == idx else curses.A_NORMAL

                if x + len(label) + 3 >= width:
                    break

                stdscr.addstr(y, x, f" {label} ", attr)
                x += len(label) + 3

            if end < len(options):
                stdscr.addstr(y, min(x, width - 4), " >")

        if allow_manual:
            stdscr.addstr(7, 2, "Type to enter a manual value:")
            stdscr.addstr(8, 2, typed)

        stdscr.addstr(height - 2, 2, "Left/Right: browse | Enter: accept | Esc: back", curses.A_DIM)

        stdscr.refresh()
        key = stdscr.getch()

        if key == ESCAPE:
            return None

        if key == curses.KEY_LEFT:
            if options:
                idx = max(0, idx - 1)

        elif key == curses.KEY_RIGHT:
            if options:
                idx = min(len(options) - 1, idx + 1)

        elif key in ENTER_KEYS:
            if typed.strip():
                return typed.strip()

            if options:
                return options[idx]

            return None

        elif key in {curses.KEY_BACKSPACE, 127, 8}:
            typed = typed[:-1]

        elif allow_manual and 32 <= key <= 126:
            typed += chr(key)

def choose_vertical(
    stdscr,
    title: str,
    options: list[str],
    *,
    allow_escape: bool = True,
) -> str | None:
    """
    Single-select vertical menu.

    Up/Down moves the selection.
    Enter accepts.
    Escape returns None.
    """
    curses.curs_set(0)

    if not options:
        return None

    selected_idx = 0
    scroll = 0

    while True:
        stdscr.clear()

        height, width = stdscr.getmaxyx()
        visible_count = max(1, height - 6)

        if selected_idx < scroll:
            scroll = selected_idx
        elif selected_idx >= scroll + visible_count:
            scroll = selected_idx - visible_count + 1

        safe_addstr(stdscr, 1, 2, title, curses.A_BOLD)

        y = 3
        end = min(len(options), scroll + visible_count)

        for idx in range(scroll, end):
            option = options[idx]

            attr = curses.A_REVERSE if idx == selected_idx else curses.A_NORMAL
            marker = ">" if idx == selected_idx else " "

            safe_addstr(
                stdscr,
                y,
                2,
                f"{marker} {option}",
                attr,
            )

            y += 1

        footer = "Up/Down: move | Enter: select"
        if allow_escape:
            footer += " | Esc: back"

        safe_addstr(stdscr, height - 2, 2, footer, curses.A_DIM)

        if scroll > 0:
            safe_addstr(stdscr, 2, width - 10, "more ↑", curses.A_DIM)

        if end < len(options):
            safe_addstr(stdscr, height - 3, width - 10, "more ↓", curses.A_DIM)

        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_DOWN:
            selected_idx = min(selected_idx + 1, len(options) - 1)

        elif key == curses.KEY_UP:
            selected_idx = max(selected_idx - 1, 0)

        elif key in ENTER_KEYS:
            return options[selected_idx]

        elif key == ESCAPE and allow_escape:
            return None

def choose_vertical_multi(
    stdscr,
    title: str,
    options: list[str],
    *,
    allow_escape: bool = True,
) -> list[str] | None:
    """
    Multi-select vertical menu.

    Up/Down moves the selection.
    Space toggles the current option.
    Enter accepts selected options.
    Escape returns None.
    """
    curses.curs_set(0)

    if not options:
        return []

    selected_idx = 0
    scroll = 0
    selected_values: set[str] = set()

    while True:
        stdscr.clear()

        height, width = stdscr.getmaxyx()
        visible_count = max(1, height - 7)

        if selected_idx < scroll:
            scroll = selected_idx
        elif selected_idx >= scroll + visible_count:
            scroll = selected_idx - visible_count + 1

        safe_addstr(stdscr, 1, 2, title, curses.A_BOLD)
        safe_addstr(
            stdscr,
            2,
            2,
            "Use Space to toggle items. Press Enter when done.",
            curses.A_DIM,
        )

        y = 4
        end = min(len(options), scroll + visible_count)

        for idx in range(scroll, end):
            option = options[idx]

            is_selected = option in selected_values

            checkbox = "[x]" if is_selected else "[ ]"
            cursor = ">" if idx == selected_idx else " "

            attr = curses.A_REVERSE if idx == selected_idx else curses.A_NORMAL

            safe_addstr(
                stdscr,
                y,
                2,
                f"{cursor} {checkbox} {option}",
                attr,
            )

            y += 1

        footer = "Up/Down: move | Space: toggle | Enter: accept"
        if allow_escape:
            footer += " | Esc: back"

        safe_addstr(stdscr, height - 2, 2, footer, curses.A_DIM)

        if scroll > 0:
            safe_addstr(stdscr, 3, width - 10, "more ↑", curses.A_DIM)

        if end < len(options):
            safe_addstr(stdscr, height - 3, width - 10, "more ↓", curses.A_DIM)

        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_DOWN:
            selected_idx = min(selected_idx + 1, len(options) - 1)

        elif key == curses.KEY_UP:
            selected_idx = max(selected_idx - 1, 0)

        elif key in SPACE_KEYS:
            value = options[selected_idx]

            if value in selected_values:
                selected_values.remove(value)
            else:
                selected_values.add(value)

        elif key in ENTER_KEYS:
            return [
                option for option in options
                if option in selected_values
            ]

        elif key == ESCAPE and allow_escape:
            return None

def prompt(msg: str) -> str:
    return input(f"{msg}: ").strip()

def choose_option(title: str, options: list[str]) -> str:
    print(f"\n{title}")

    for i, opt in enumerate(options):
        print(f"{i + 1}. {opt}")

    while True:
        raw = prompt("Select")
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]

        print("Invalid selection.")