from PIL import Image
from capture_and_print import capture_and_print

image = Image.open("test_images/test.jpg")   # 手元にあるJPEG

capture_and_print(image=image)
