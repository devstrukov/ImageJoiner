import base64
import io

import matplotlib

matplotlib.use('Agg')
import numpy as np
from matplotlib import pyplot as plt
from PIL import Image, ImageDraw


def _to_rgb(image):
    # Приводим все изображения к RGB, чтобы каналы и гистограммы считались одинаково.
    if image.mode == 'RGBA':
        bg = Image.new('RGB', image.size, (255, 255, 255))
        bg.paste(image, mask=image.split()[3])
        return bg
    return image.convert('RGB')


def merge_images(img_path_1, img_path_2, direction='horizontal', output_path=None):
    # Склейка двух изображений в одно: либо рядом (horizontal), либо одно над другим (vertical).
    if output_path is None:
        output_path = 'upload/merged.jpg'
    img1 = _to_rgb(Image.open(img_path_1))
    img2 = _to_rgb(Image.open(img_path_2))

    if direction == 'horizontal':
        new_width = img1.width + img2.width
        new_height = max(img1.height, img2.height)

        result = Image.new('RGB', [new_width, new_height])
        result.paste(img1, (0, 0))
        result.paste(img2, (img1.width, 0))
        result.save(output_path)

        return result
    if direction == 'vertical':
        new_width = max(img1.width, img2.width)
        new_height = img1.height + img2.height

        result = Image.new('RGB', [new_width, new_height])
        result.paste(img1, (0, 0))
        result.paste(img2, (0, img1.height))
        result.save(output_path)

        return result
    return None


def histograms(image_path, title):
    # Локальный вариант для ручной отладки (рисует окно matplotlib).
    image = Image.open(image_path)
    img = np.array(_to_rgb(image))
    x = np.arange(256)

    plt.figure(figsize=(16, 4))

    plt.subplot(1, 4, 1)
    plt.imshow(img)
    plt.title(title)
    plt.axis('off')

    for i, color, name in zip([0, 1, 2], ['red', 'green', 'blue'], ['R', 'G', 'B']):
        plt.subplot(1, 4, i + 2)
        # Используем явный расчет частот, чтобы избежать ошибок совместимости
        # matplotlib/numpy в разных окружениях.
        channel = img[:, :, i].astype(np.uint8)
        hist = np.bincount(channel.ravel(), minlength=256)
        plt.bar(x, hist, width=1.0, color=color, alpha=0.7)
        plt.title(f'{name}-канал')
        plt.xlabel('Интенсивность')
        plt.ylabel('Пиксели')
        plt.xlim(0, 255)

    plt.tight_layout()
    plt.show()


def histogram_figure_base64(image_path, title):
    """
    Возвращает PNG в base64 для HTML.
    В веб-версии используем Pillow-рендер (без matplotlib), чтобы избежать
    platform-specific ошибок на PaaS (например Render).
    """
    image = _to_rgb(Image.open(image_path))

    # Макет: превью + три графика (R/G/B) по 256 бинов каждый.
    panel_w, panel_h = 280, 240
    margin = 20
    gap = 20
    width = margin + panel_w + gap + panel_w + gap + panel_w + gap + panel_w + margin
    height = margin * 2 + panel_h + 30

    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)

    # Панель 1: исходное изображение
    preview = image.copy()
    preview.thumbnail((panel_w - 20, panel_h - 20))
    px = margin + (panel_w - preview.width) // 2
    py = margin + (panel_h - preview.height) // 2
    canvas.paste(preview, (px, py))
    draw.rectangle([margin, margin, margin + panel_w, margin + panel_h], outline="black", width=1)
    draw.text((margin + 8, margin + panel_h + 8), title, fill="black")

    # Панели 2..4: гистограммы каналов
    channels = image.split()
    labels = [("R-канал", (220, 60, 60)), ("G-канал", (60, 170, 60)), ("B-канал", (70, 100, 220))]

    for idx, (channel, (label, color)) in enumerate(zip(channels, labels), start=1):
        x0 = margin + idx * (panel_w + gap)
        y0 = margin
        x1 = x0 + panel_w
        y1 = y0 + panel_h

        draw.rectangle([x0, y0, x1, y1], outline="black", width=1)
        draw.text((x0 + 8, y1 + 8), label, fill="black")

        hist = channel.histogram()[:256]
        max_v = max(hist) if hist else 1
        if max_v == 0:
            max_v = 1

        graph_margin_x = 10
        graph_margin_y = 10
        graph_w = panel_w - graph_margin_x * 2
        graph_h = panel_h - graph_margin_y * 2

        for bin_i, val in enumerate(hist):
            bar_h = int((val / max_v) * graph_h)
            bx = x0 + graph_margin_x + int((bin_i / 255) * (graph_w - 1))
            by = y0 + panel_h - graph_margin_y
            draw.line([(bx, by), (bx, by - bar_h)], fill=color, width=1)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")