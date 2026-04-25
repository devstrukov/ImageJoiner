import os
import random
import time
import uuid

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from utils import histogram_figure_base64, merge_images

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-change-me')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(_BASE_DIR, 'upload')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'webp'}

_CAPTCHA_MIN = 2
_CAPTCHA_MAX = 19
_UPLOAD_TTL_SECONDS = 30 * 60


def _refresh_captcha():
    # Генерируем простую арифметическую капчу и кладем правильный ответ в сессию.
    a = random.randint(_CAPTCHA_MIN, _CAPTCHA_MAX)
    b = random.randint(_CAPTCHA_MIN, _CAPTCHA_MAX)
    session['captcha_answer'] = a + b
    return a, b


def _allowed_file(filename):
    # Разрешаем только заранее заданные расширения изображений.
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def _cleanup_old_uploads(folder, max_age_seconds=_UPLOAD_TTL_SECONDS):
    # Удаляем старые файлы загрузок, чтобы папка upload не разрасталась бесконечно.
    now = time.time()
    if not os.path.isdir(folder):
        return
    for entry in os.scandir(folder):
        if not entry.is_file():
            continue
        try:
            file_age = now - entry.stat().st_mtime
            if file_age > max_age_seconds:
                os.remove(entry.path)
        except OSError:
            # Если файл уже удален или недоступен, просто пропускаем его.
            continue


@app.route('/')
def index():
    captcha_a, captcha_b = _refresh_captcha()
    return render_template(
        'index.html',
        captcha_a=captcha_a,
        captcha_b=captcha_b,
    )


@app.route('/results', methods=['POST'])
def results():
    # 1) Сначала антибот-проверка, чтобы не тратить ресурсы на обработку мусорных запросов.
    raw_captcha = request.form.get('captcha_answer', '').strip()
    try:
        user_captcha = int(raw_captcha)
    except ValueError:
        flash('Введите ответ в поле проверки числом.')
        return redirect(url_for('index'))
    if user_captcha != session.get('captcha_answer'):
        flash('Неверный ответ в поле проверки «не робот».')
        return redirect(url_for('index'))
    session.pop('captcha_answer', None)

    # 2) Затем проверяем и сохраняем два входных файла.
    f1 = request.files.get('image1')
    f2 = request.files.get('image2')
    if not f1 or not f2:
        flash('Нужно загрузить оба изображения.')
        return redirect(url_for('index'))
    if f1.filename == '' or f2.filename == '':
        flash('Файлы не выбраны.')
        return redirect(url_for('index'))
    if not _allowed_file(f1.filename) or not _allowed_file(f2.filename):
        flash('Допустимы только изображения: PNG, JPG, JPEG, BMP, WEBP.')
        return redirect(url_for('index'))

    orientation = request.form.get('orientation', 'vertical')
    if orientation not in ('vertical', 'horizontal'):
        orientation = 'vertical'

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    ext1 = f1.filename.rsplit('.', 1)[1].lower()
    ext2 = f2.filename.rsplit('.', 1)[1].lower()
    token = uuid.uuid4().hex
    name1 = f'{token}_1.{ext1}'
    name2 = f'{token}_2.{ext2}'
    name_merged = f'{token}_merged.jpg'

    path1 = os.path.join(app.config['UPLOAD_FOLDER'], name1)
    path2 = os.path.join(app.config['UPLOAD_FOLDER'], name2)
    merged_path = os.path.join(app.config['UPLOAD_FOLDER'], name_merged)

    f1.save(path1)
    f2.save(path2)

    # 3) Склеиваем изображения согласно выбранной ориентации.
    try:
        merge_images(path1, path2, direction=orientation, output_path=merged_path)
    except Exception as exc:
        flash(f'Ошибка при склейке изображений: {exc}')
        return redirect(url_for('index'))

    # 4) Строим три набора гистограмм: для двух исходников и результирующего изображения.
    try:
        hist1 = histogram_figure_base64(path1, 'Изображение 1')
        hist2 = histogram_figure_base64(path2, 'Изображение 2')
        hist3 = histogram_figure_base64(merged_path, 'Склеенное изображение')
    except Exception as exc:
        flash(f'Ошибка при построении гистограмм: {exc}')
        return redirect(url_for('index'))

    # Фоновая housekeeping-очистка старых файлов без отдельного cron.
    _cleanup_old_uploads(app.config['UPLOAD_FOLDER'])

    return render_template(
        'results.html',
        hist1=hist1,
        hist2=hist2,
        hist3=hist3,
        image1_url=url_for('uploaded_file', name=name1),
        image2_url=url_for('uploaded_file', name=name2),
        merged_url=url_for('uploaded_file', name=name_merged),
        orientation=orientation,
    )


@app.route('/upload/<name>')
def uploaded_file(name):
    # Маршрут только для чтения ранее сохраненных файлов (используется <img src=...>).
    safe = secure_filename(name)
    if safe != name or not safe:
        abort(404)
    full = os.path.join(app.config['UPLOAD_FOLDER'], safe)
    if not os.path.isfile(full):
        abort(404)
    return send_from_directory(app.config['UPLOAD_FOLDER'], safe)


if __name__ == '__main__':
    app.run(debug=True)
