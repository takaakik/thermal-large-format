#!/usr/bin/env python3

from __future__ import annotations

import argparse
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


def capture_frame() -> Image.Image:
    """USBカメラから最高解像度の画像を1枚取得する。"""
    cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)

    if not cap.isOpened():
        raise RuntimeError(f"カメラを開けませんでした: {CAMERA_DEVICE}")

    try:
        cap.set(
            cv2.CAP_PROP_FOURCC,
            cv2.VideoWriter_fourcc(*"MJPG"),
        )
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)

        # 自動露出やオートフォーカスが落ち着くのを待つ
        time.sleep(1.0)

        frame = None

        # 最初の数フレームは捨てる
        for _ in range(10):
            ok, frame = cap.read()

            if not ok:
                raise RuntimeError("カメラから画像を取得できませんでした")

        if frame is None:
            raise RuntimeError("取得画像が空です")

        actual_height, actual_width = frame.shape[:2]
        print(f"Capture: {actual_width}x{actual_height}")

        # OpenCVのBGRをRGBへ変換
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

    finally:
        cap.release()


def prepare_for_print(
    image: Image.Image,
    rotate_clockwise: bool,
) -> Image.Image:
    """撮影画像をA4・203dpiのグレースケール画像に変換する。"""
    if rotate_clockwise:
        # カメラを横長の状態で使い、出力だけ縦へ回す場合
        image = image.transpose(Image.Transpose.ROTATE_270)

    image = ImageOps.exif_transpose(image)

    # A4の縦横比に中央クロップしつつ、印刷解像度へ縮小
    image = ImageOps.fit(
        image,
        (PRINT_WIDTH, PRINT_HEIGHT),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )

    # まずはドライバの階調処理を確認するため8bitグレーのまま
    return image.convert("L")


def print_image(path: Path) -> None:
    """CUPS経由でM08Fへ画像を送る。"""
    command = [
        "lp",
        "-d",
        PRINTER_NAME,
        "-o",
        "media=A4",
        "-o",
        "fit-to-page",
        str(path),
    ]

    print("Print command:", " ".join(command))
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )

    if result.stdout:
        print(result.stdout.strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture an image and print it on the M08F."
    )

    parser.add_argument(
        "--print",
        action="store_true",
        dest="send_to_printer",
        help="保存後にM08Fへ印刷する",
    )

    parser.add_argument(
        "--no-rotate",
        action="store_true",
        help="撮影画像を90度回転しない",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    original_path = OUTPUT_DIR / f"{timestamp}-original.jpg"
    print_path = OUTPUT_DIR / f"{timestamp}-print.png"

    try:
        original = capture_frame()
        original.save(original_path, quality=95)
        print(f"Original saved: {original_path}")

        prepared = prepare_for_print(
            original,
            rotate_clockwise=not args.no_rotate,
        )
        prepared.save(print_path, dpi=(203, 203))
        print(f"Print image saved: {print_path}")
        print(f"Print size: {prepared.width}x{prepared.height}")

        if args.send_to_printer:
            print_image(print_path)
        else:
            print("Dry run: 印刷はしていません。")
            print("印刷する場合: python capture_and_print.py --print")

        return 0

    except subprocess.CalledProcessError as exc:
        print("印刷コマンドが失敗しました。", file=sys.stderr)

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
