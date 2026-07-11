from PIL import Image, ImageDraw

WIDTH = 1678
HEIGHT = 2373

image = Image.new("L", (WIDTH, HEIGHT), 255)
draw = ImageDraw.Draw(image)

# 上部：16段階のグレースケール
steps = 16
bar_top = 100
bar_height = 300
bar_width = WIDTH // steps

for i in range(steps):
    gray = round(255 * i / (steps - 1))
    x0 = i * bar_width
    x1 = WIDTH if i == steps - 1 else (i + 1) * bar_width
    draw.rectangle((x0, bar_top, x1, bar_top + bar_height), fill=gray)

# 中央：連続グラデーション
gradient_top = 550
gradient_height = 500

for x in range(WIDTH):
    gray = round(255 * x / (WIDTH - 1))
    draw.line(
        (x, gradient_top, x, gradient_top + gradient_height),
        fill=gray,
    )

# 下部：線幅テスト
y = 1300
for width in (1, 2, 3, 4, 6, 8, 12, 16):
    draw.line((100, y, WIDTH - 100, y), fill=0, width=width)
    y += 80

# 印刷可能範囲確認用の枠
draw.rectangle(
    (10, 10, WIDTH - 11, HEIGHT - 11),
    outline=0,
    width=4,
)

image.save("m08f-test.png", dpi=(203, 203))
print(f"Saved m08f-test.png: {WIDTH}x{HEIGHT}px")
