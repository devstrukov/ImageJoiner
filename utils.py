import base64
import io

import matplotlib

matplotlib.use('Agg')
import numpy as np
from matplotlib import pyplot as plt
from PIL import Image


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
    """Те же графики, что в histograms, но PNG в base64 для вставки в HTML."""
    image = Image.open(image_path)
    img = np.array(_to_rgb(image))
    x = np.arange(256)

    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    axes[0].imshow(img)
    axes[0].set_title(title)
    axes[0].axis('off')

    for i, color, name in zip([0, 1, 2], ['red', 'green', 'blue'], ['R', 'G', 'B']):
        ax = axes[i + 1]
        channel = img[:, :, i].astype(np.uint8)
        hist = np.bincount(channel.ravel(), minlength=256)
        ax.bar(x, hist, width=1.0, color=color, alpha=0.7)
        ax.set_title(f'{name}-канал')
        ax.set_xlabel('Интенсивность')
        ax.set_ylabel('Пиксели')
        ax.set_xlim(0, 255)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('ascii')