import cv2
import sys
from pathlib import Path

DEVICE = "/dev/video0"
WIDTH = 3264
HEIGHT = 2448
OUTPUT = Path("capture-test.jpg")


def main() -> int:
    cap = cv2.VideoCapture(DEVICE, cv2.CAP_V4L2)

    if not cap.isOpened():
        print(f"カメラを開けませんでした: {DEVICE}", file=sys.stderr)
        return 1

    # 高解像度ではMJPEGを明示
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    # 露出・AFが安定するまで数フレーム捨てる
    frame = None
    for _ in range(10):
        ok, frame = cap.read()
        if not ok:
            cap.release()
            print("画像取得に失敗しました", file=sys.stderr)
            return 1

    cap.release()

    actual_height, actual_width = frame.shape[:2]
    print(f"取得サイズ: {actual_width}x{actual_height}")

    if not cv2.imwrite(str(OUTPUT), frame, [cv2.IMWRITE_JPEG_QUALITY, 95]):
        print("JPEG保存に失敗しました", file=sys.stderr)
        return 1

    print(f"保存しました: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
