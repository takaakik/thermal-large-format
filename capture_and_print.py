#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
from PIL import Image, ImageOps


CAMERA_DEVICE = "/dev/video0"
CAPTURE_WIDTH = 3264
CAPTURE_HEIGHT = 2448

# M08F: A4 at 203 dpi
PRINT_WIDTH = 1678
PRINT_HEIGHT = 2373

OUTPUT_DIR = Path("output")
PRINTER_NAME = "M08F"
PRINTER_URI_PART = "usb:///M08F"
PRINT_TIMEOUT_SECONDS = 300

# Absolute paths are used because systemd may not include /usr/sbin in PATH.
LPINFO = "/usr/sbin/lpinfo"
LPSTAT = "/usr/bin/lpstat"
LP = "/usr/bin/lp"
CANCEL = "/usr/bin/cancel"


def run_command(
    command: list[str],
    *,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run an external command and capture stdout/stderr."""
    return subprocess.run(
        command,
        check=check,
        capture_output=True,
        text=True,
    )


def get_pending_jobs() -> str:
    """Return pending CUPS jobs for the M08F as text."""
    result = run_command(
        [LPSTAT, "-W", "not-completed", "-o", PRINTER_NAME]
    )
    return result.stdout.strip()


def check_printer_ready() -> None:
    """
    Confirm that the M08F is connected, enabled, accepting jobs,
    and has no unfinished jobs.
    """
    devices = run_command([LPINFO, "-v"])

    if PRINTER_URI_PART not in devices.stdout:
        raise RuntimeError(
            "M08F is not detected as a USB printer. "
            "Check printer power, paper, and the USB cable."
        )

    status = run_command([LPSTAT, "-p", PRINTER_NAME])
    status_text = f"{status.stdout}\n{status.stderr}".lower()

    if status.returncode != 0:
        raise RuntimeError(
            f"CUPS printer '{PRINTER_NAME}' is not registered."
        )

    if "disabled" in status_text:
        raise RuntimeError(
            "M08F is disabled in CUPS. Run: sudo cupsenable M08F"
        )

    accepting = run_command([LPSTAT, "-a", PRINTER_NAME])
    accepting_text = f"{accepting.stdout}\n{accepting.stderr}".lower()

    if (
        accepting.returncode != 0
        or "accepting requests" not in accepting_text
    ):
        raise RuntimeError(
            "M08F is not accepting print jobs. "
            "Run: sudo cupsaccept M08F"
        )

    pending = get_pending_jobs()
    if pending:
        raise RuntimeError(
            "M08F already has unfinished print jobs. "
            "Clear them before shooting:\n"
            f"{pending}\n"
            "Command: cancel -a M08F"
        )


def capture_frame() -> Image.Image:
    """Capture one full-resolution frame from the USB camera."""
    cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera: {CAMERA_DEVICE}")

    try:
        cap.set(
            cv2.CAP_PROP_FOURCC,
            cv2.VideoWriter_fourcc(*"MJPG"),
        )
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)

        # Give auto-exposure and autofocus time to settle.
        time.sleep(1.0)

        frame = None
        for _ in range(10):
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError("Failed to capture an image.")

        if frame is None:
            raise RuntimeError("Captured frame is empty.")

        actual_height, actual_width = frame.shape[:2]
        print(f"Capture: {actual_width}x{actual_height}")

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

    finally:
        cap.release()


def prepare_for_print(
    image: Image.Image,
    *,
    rotate_clockwise: bool = True,
) -> Image.Image:
    """Convert a captured image to A4/203 dpi grayscale."""
    image = ImageOps.exif_transpose(image)

    if rotate_clockwise:
        image = image.transpose(Image.Transpose.ROTATE_270)

    image = ImageOps.fit(
        image,
        (PRINT_WIDTH, PRINT_HEIGHT),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )

    return image.convert("L")


def send_to_printer(path: Path) -> str:
    """Submit one image to CUPS and return its job ID."""
    command = [
        LP,
        "-d",
        PRINTER_NAME,
        "-o",
        "media=A4",
        "-o",
        "fit-to-page",
        str(path),
    ]

    print("Print command:", " ".join(command))

    result = run_command(command, check=True)
    message = result.stdout.strip()

    if message:
        print(message)

    match = re.search(r"request id is (\S+)", message)
    if not match:
        raise RuntimeError(
            f"Could not read the CUPS job ID from: {message}"
        )

    return match.group(1)


def get_active_job_ids() -> set[str]:
    """Return IDs of unfinished M08F jobs."""
    result = run_command(
        [LPSTAT, "-W", "not-completed", "-o", PRINTER_NAME]
    )

    return {
        line.split()[0]
        for line in result.stdout.splitlines()
        if line.strip()
    }


def cancel_job(job_id: str) -> None:
    """Cancel one CUPS job."""
    run_command([CANCEL, job_id])


def wait_until_print_finished(
    job_id: str,
    *,
    timeout_seconds: int = PRINT_TIMEOUT_SECONDS,
) -> None:
    """Wait until one submitted job completes."""
    print(f"Waiting for print job: {job_id}")
    deadline = time.monotonic() + timeout_seconds

    while True:
        if job_id not in get_active_job_ids():
            print(f"Print finished: {job_id}")
            return

        printer_status = run_command([LPSTAT, "-p", PRINTER_NAME])
        status_text = (
            f"{printer_status.stdout}\n{printer_status.stderr}"
        ).lower()

        if "disabled" in status_text:
            cancel_job(job_id)
            raise RuntimeError(
                "M08F became disabled during printing. "
                f"Job {job_id} was cancelled."
            )

        if time.monotonic() >= deadline:
            cancel_job(job_id)
            raise TimeoutError(
                f"Printing did not finish within {timeout_seconds} seconds. "
                f"Job {job_id} was cancelled."
            )

        time.sleep(1.0)


def capture_and_print(
    *,
    print_enabled: bool = True,
    rotate_clockwise: bool = True,
) -> tuple[Path, Path]:
    """
    Capture, prepare an A4 image, and optionally print it.

    Returns:
        (original image path, print image path)
    """
    if print_enabled:
        print("Checking printer...")
        check_printer_ready()
        print("Printer ready.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    original_path = OUTPUT_DIR / f"{timestamp}-original.jpg"
    print_path = OUTPUT_DIR / f"{timestamp}-print.png"

    print("Starting capture...")
    original = capture_frame()

    original.save(original_path, quality=95)
    print(f"Original saved: {original_path}")

    prepared = prepare_for_print(
        original,
        rotate_clockwise=rotate_clockwise,
    )
    prepared.save(print_path, dpi=(203, 203))

    print(f"Print image saved: {print_path}")
    print(f"Print size: {prepared.width}x{prepared.height}")

    if print_enabled:
        job_id = send_to_printer(print_path)
        wait_until_print_finished(job_id)
    else:
        print("Print disabled: image files only.")

    return original_path, print_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture an image and print it on the M08F."
    )
    parser.add_argument(
        "--no-print",
        action="store_true",
        help="Capture and save images without printing.",
    )
    parser.add_argument(
        "--no-rotate",
        action="store_true",
        help="Do not rotate the captured image by 90 degrees.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        capture_and_print(
            print_enabled=not args.no_print,
            rotate_clockwise=not args.no_rotate,
        )
        return 0

    except subprocess.CalledProcessError as exc:
        print(f"External command failed: {exc}", file=sys.stderr)
        if exc.stdout:
            print(exc.stdout, file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        return 1

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
