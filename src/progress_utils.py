"""Utility functions for tracking download progress using the Rich library.
It includes features for creating a progress bar and a formatted progress table
specifically designed for monitoring the download status of the current taks.

It also exposes a JSON progress file (progress.json) that mirrors the current
download state, meant to be read by external dashboards (e.g. Glance).
"""
import json
import logging
import threading
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.prompt import Prompt
from rich.table import Table

# progetto/backend/src/progress_utils.py -> progetto/frontend/static/progress.json
PROGRESS_FILE = (
    Path(__file__).resolve().parents[2] / "frontend" / "static" / "progress.json"
)

# Stato condiviso in memoria per il processo di download.
# NB: se manga_downloader.py viene lanciato come subprocess separato da app.py,
# questo stato vive SOLO in quel processo: la condivisione con Flask avviene
# esclusivamente tramite il file su disco (PROGRESS_FILE), non tramite import.
_progress_lock = threading.Lock()
_progress_state: dict = {}


def init_progress_state(manga_name: str, chapter_labels: list[str]) -> None:
    """Initialize the in-memory progress state and write the first progress.json."""
    global _progress_state
    with _progress_lock:
        _progress_state = {
            "manga_name": manga_name,
            "chapters": {
                label: {"label": label, "percentage": 0.0, "done": False}
                for label in chapter_labels
            },
        }
    write_progress_file()


def update_chapter_progress(label: str, percentage: float) -> None:
    """Update the progress of a single chapter and persist the new state to disk."""
    with _progress_lock:
        chapter = _progress_state.get("chapters", {}).get(label)
        if chapter is not None:
            chapter["percentage"] = round(percentage, 1)
            chapter["done"] = percentage >= 100

    write_progress_file()


def write_progress_file() -> None:
    """Serialize the current progress state to PROGRESS_FILE (atomic write).

    Everything (build data + write tmp file + rename) happens under the same
    lock: multiple worker threads call this several times per second, and if
    the write itself weren't serialized too, two threads could race on the
    same .tmp path and make Path.replace() raise FileNotFoundError, killing
    the calling download thread silently. A failure here must also never be
    allowed to propagate and abort an actual page download, so it's caught
    and just logged.
    """
    with _progress_lock:
        chapters = list(_progress_state.get("chapters", {}).values())
        total = len(chapters)
        completed = sum(1 for chapter in chapters if chapter["done"])
        overall_pct = (
            sum(chapter["percentage"] for chapter in chapters) / total
            if total
            else 0.0
        )

        data = {
            "manga_name": _progress_state.get("manga_name", ""),
            "overall": {
                "percentage": round(overall_pct, 1),
                "completed": completed,
                "total": total,
            },
            "chapters": chapters,
        }

        try:
            PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = PROGRESS_FILE.with_suffix(".tmp")
            with tmp_path.open("w", encoding="utf-8") as file:
                json.dump(data, file)
            # Rename atomico: evita che glance legga un file a metà scrittura
            tmp_path.replace(PROGRESS_FILE)
        except OSError as os_err:
            logging.warning(f"Could not write progress.json: {os_err}")


def reset_progress_file() -> None:
    """Reset progress.json at the start/end of a full run (optional helper)."""
    global _progress_state
    with _progress_lock:
        _progress_state = {}
    write_progress_file()


def create_progress_bar() -> Progress:
    """Create a progress bar for tracking download progress."""
    return Progress(
        "{task.description}",
        SpinnerColumn(),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        "•",
        TimeRemainingColumn(),
    )


def create_progress_table(title: str, job_progress: Progress) -> Table:
    """Create a formatted progress table for tracking the download status."""
    progress_table = Table.grid()
    progress_table.add_row(
        Panel.fit(
            job_progress,
            title=f"[b]{title}",
            border_style="red",
            padding=(1, 1),
        ),
    )
    return progress_table


def create_select_items_list(items: list[str], display_limit: int = 15) -> list[int]:
    """Show a numbered list of items and allow the user to select one or more indexes.
    Return the list of selected 0-based indexes
    If there are more than 15 volumes,
        return the list in a compact format like this:
        [1] Volume 01
        ...
        [15] Volume 15
    """
    console = Console()
    console.print("[bold]Please select volume(s) to download[/bold]")
    # Compact list format
    if len(items) > display_limit:
        console.print(
            f"[cyan][1][/cyan] {items[0]}\n...\n"
            f"[cyan][{len(items)}][/cyan] {items[-1]}",
        )
    else:
        for indx, item in enumerate(items):
            console.print(f"[cyan][{indx + 1}][/cyan] {item}")

    prompt_text = "Enter the numbers separated by commas (e.g. 1,3,5) or 'all' for all:"
    choice = Prompt.ask(f"\n{prompt_text}", default="all")

    if choice.strip().lower() == "all":
        return list(range(len(items)))

    # Parse user input safely without raising exceptions
    raw_indexes = [int(x.strip()) - 1 for x in choice.split(",") if x.strip().isdigit()]
    valid_indexes = [indx for indx in raw_indexes if 0 <= indx < len(items)]

    if not valid_indexes:
        console.print("[red]No valid selections made.[/red]")

    return valid_indexes
