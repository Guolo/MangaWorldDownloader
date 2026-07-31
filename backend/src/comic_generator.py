"""Module that provides functionality to generate comic files from images.

It processes directories recursively and generates comic files such as PDF and CBZ from
image collections found in each directory.
"""

import logging
import os
import re
import zipfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from rich.progress import Progress

from .config import DOWNLOAD_FOLDER, IMAGE_FORMATS_FOR_PDF


def count_subsubfolders(main_folder: str) -> int:
    """Count the total number of subsubfolders in a given main folder."""
    total_subsubfolders = 0
    for root, dirs, _ in os.walk(main_folder):
        if root.count(os.sep) == main_folder.count(os.sep) + 1:
            total_subsubfolders += len(dirs)

    return total_subsubfolders


def convert2cbz(image_paths: list[Path], output_cbz_path: str, base_folder: Path | None = None) -> None:
    """Convert a list of image paths into a CBZ archive.

    If base_folder is provided, the internal archive name preserves the path
    relative to base_folder (e.g. 'Chapter 1/3.jpg'), avoiding name collisions
    when images from multiple subfolders (chapters) share the same filename.
    Otherwise, only the filename is used (safe for a single flat folder).
    """
    if not image_paths:
        logging.error("No images provided to convert.")
        return

    output_cbz = Path(output_cbz_path)

    with zipfile.ZipFile(
        output_cbz,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as cbz_file:
        for image_path in image_paths:
            if base_folder is not None:
                arcname = str(image_path.relative_to(base_folder))
            else:
                arcname = image_path.name

            cbz_file.write(
                image_path,
                arcname=arcname,
            )

    logging.info("CBZ created: %s", output_cbz)


def convert2pdf(image_paths: list, output_pdf_path: str) -> None:
    """Convert a list of image paths into a PDF file."""
    if not image_paths:
        logging.error("No images provided to convert.")
        return

    pics = []
    for img_path in image_paths:
        try:
            img = Image.open(img_path)
            pics.append(img.convert("RGB"))

        except UnidentifiedImageError:
            log_message = f"Unrecognized image format: {img_path}"
            logging.warning(log_message)

        except OSError as os_err:
            log_message = f"OS error when processing {img_path}: {os_err}"
            logging.warning(log_message)

    if pics:
        output_pdf = Path(output_pdf_path)
        pics[0].save(
            output_pdf,
            "PDF",
            resolution=100.0,
            save_all=True,
            append_images=pics[1:],
        )
        log_message = f"PDF created: {output_pdf}"
        logging.info(log_message)

    else:
        logging.error("No valid images to convert.")


def get_num_folders(current_directory: str) -> int:
    """Count the number of directories in the specified directory."""
    return sum(1 for entry in os.scandir(current_directory) if entry.is_dir())

def extract_number(file_path: str) -> tuple:
    """Extract the number of the images by path name and file name."""
    nums = re.findall(r"\d+", file_path)
    return tuple(int(n) for n in nums) if nums else (0,)

def collect_image_paths(folder: str) -> list[str]:
    """Collect and sort all supported image paths from a folder."""
    # Use rglob to recursively search for all images with valid extensions
    image_paths = [
        file for file in Path(folder).rglob("*")
        if file.suffix.lower() in IMAGE_FORMATS_FOR_PDF
    ]

    image_paths.sort(
        key=lambda path: (extract_number(str(path.parent)), extract_number(path.name)),
    )
    return image_paths


def generate_file_from_folder(folder_path: str, *, output_format: str, output_name: str | None = None) -> None:
    """Generate a comic file from all images contained in a folder.

    The output format can be either PDF or CBZ.
    """
    image_paths = collect_image_paths(folder_path)

    if not image_paths:
        return

    folder = Path(folder_path)
    file_stem = output_name if output_name else folder.name
    output_path = Path.cwd() / folder.parent / f"{file_stem}.{output_format}"

    if output_format.lower() == "pdf":
        convert2pdf(image_paths, str(output_path))
    elif output_format.lower() == "cbz":
        convert2cbz(image_paths, str(output_path), base_folder=folder)
    else:
        log_message = f"Unsupported output format: {output_format}"
        raise ValueError(log_message)


def generate_comic_files(
    parent_folder: str,
    job_progress: Progress,
    *,
    is_module: bool = False,
    single_file: bool = False,
    output_format: str = "pdf",
    output_name: str | None = None,
    target_folders: list[str] | None = None,
) -> None:
    """Generate comic files from images in each subfolder of the parent folder.

    If target_folders is provided (list of subfolder names), only those specific
    subfolders are processed instead of walking the entire parent_folder tree.
    This avoids re-generating files for unrelated folders (e.g. old volumes)
    that happen to live alongside the newly downloaded content.
    """
    if single_file:
        task = job_progress.add_task(
            f"[cyan]Generating {output_format.upper()} files",
            total=1,
        )
        generate_file_from_folder(parent_folder, output_format=output_format, output_name=output_name)
        job_progress.advance(task)
        return

    if target_folders is not None:
        task = job_progress.add_task(
            f"[cyan]Generating {output_format.upper()} files",
            total=len(target_folders),
        )
        for folder_name in target_folders:
            folder_path = Path(parent_folder) / folder_name
            if folder_path.is_dir():
                generate_file_from_folder(str(folder_path), output_format=output_format)
            job_progress.advance(task)
        return

    num_folders = (
        count_subsubfolders(DOWNLOAD_FOLDER)
        if is_module
        else get_num_folders(parent_folder)
    )
    task = job_progress.add_task(
        f"[cyan]Generating {output_format.upper()} files",
        total=num_folders,
    )
    for path, _, _ in os.walk(parent_folder):
        manga_name = Path(path).parent.name
        if manga_name != DOWNLOAD_FOLDER:
            generate_file_from_folder(path, output_format=output_format)
            job_progress.advance(task)


def main() -> None:
    """Generate comic files from images in the download folder."""
    with Progress() as job_progress:
        generate_comic_files(f"{DOWNLOAD_FOLDER}/", job_progress, is_module=True)


if __name__ == "__main__":
    main()
