import cv2

cap = cv2.VideoCapture(0)

cv2.namedWindow("Thermal Camera", cv2.WINDOW_NORMAL)
cv2.setWindowProperty(
    "Thermal Camera",
    cv2.WND_PROP_FULLSCREEN,
    cv2.WINDOW_FULLSCREEN,
)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    cv2.imshow("Thermal Camera", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
