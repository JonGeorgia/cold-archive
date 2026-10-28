#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎮📼 Сканер холодного архива v3.2.

Структура носителя (единственный поддерживаемый формат):

  <root>/
    Игры/<Игра>/<архив>       + info/info.txt + info/cover.jpg + info/screenshots/
    Фильмы/<Фильм>/<видео>    + info/...
    Прочее/<Элемент>/<файл>   + info/...

Генерирует:
  index.html   — каталог с обложками и описаниями (единственный файл)
  catalog.md   — таблица: Имя | Тип | Путь (для быстрого просмотра)

Язык интерфейса (RU/EN) выбирается флагом --lang.
"""
import os
import sys
import json
import re
import shutil
import base64
import io
import argparse
from datetime import datetime

try:
    from PIL import Image, ImageOps
    _RESAMPLE = (Image.Resampling.LANCZOS
                 if hasattr(Image, 'Resampling') else Image.LANCZOS)
    PILLOW = True
except ImportError:
    Image = ImageOps = None
    _RESAMPLE = None
    PILLOW = False

SCHEMA_VERSION = 3
DATA_PLACEHOLDER = '__ARCHIVE_DATA__'
TEMPLATE_NAME = 'index_template.html'
TABLE_NAME = 'catalog.md'

# ---------- Расширения ----------
ARCHIVE_EXTS = ('.rar', '.zip', '.7z', '.iso',
                '.tar', '.tar.gz', '.tar.xz', '.tar.bz2', '.tgz',
                '.gz', '.xz')
VIDEO_EXTS = ('.mkv', '.mp4', '.avi', '.m4v', '.webm',
              '.mov', '.wmv', '.flv', '.mpg', '.mpeg', '.ts')
CONTENT_EXTS = ARCHIVE_EXTS + VIDEO_EXTS

COVER_NAMES = ('cover.jpg', 'cover.jpeg', 'cover.png', 'cover.webp',
               'poster.jpg', 'poster.jpeg', 'poster.png')
IMG_EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp')

CATEGORY_DIRS = {
    'игры':     'Игры',   'игра':     'Игры',
    'games':    'Игры',   'game':     'Игры',
    'фильмы':   'Фильмы', 'фильм':    'Фильмы',
    'movies':   'Фильмы', 'movie':    'Фильмы',
    'films':    'Фильмы', 'film':     'Фильмы',
    'прочее':   'Прочее', 'другое':   'Прочее',
    'other':    'Прочее', 'misc':     'Прочее',
}

# Порядок категорий в таблице
CATEGORY_ORDER = {'Игры': 0, 'Фильмы': 1, 'Прочее': 2}

SKIP_NAMES = {'$RECYCLE.BIN', 'System Volume Information',
              'SanDiskSecureAccess', 'RECYCLER', '.Trash', '.Trashes',
              'lost+found', '.archive_thumbs', 'info'}

FIELD_MAP = {
    'название': 'name', 'описание': 'description', 'жанр': 'genre',
    'год': 'year',
    'разработчик': 'developer', 'автор': 'developer', 'студия': 'developer',
    'издатель': 'publisher', 'режиссёр': 'director', 'режиссер': 'director',
    'язык': 'language', 'версия': 'version', 'серия': 'series',
    'страна': 'country', 'длительность': 'duration', 'комментарий': 'comment',
}
JSON_FIELDS = ('name', 'description', 'genre', 'year',
               'developer', 'publisher', 'director', 'language', 'version',
               'series', 'country', 'duration', 'comment')

# ---------- Локализация ----------
LANG_STRINGS = {
    'ru': {
        'title':            'Холодный архив',
        'search_placeholder': 'поиск...',
        'sort_name_asc':    'название ▲',
        'sort_name_desc':   'название ▼',
        'sort_year_desc':   'год ▼',
        'sort_year_asc':    'год ▲',
        'sort_size_desc':   'размер ▼',
        'sort_size_asc':    'размер ▲',
        'settings_title':   'Базовый путь для копирования',
        'counter_items':    'элементов',
        'counter_shown':    'показано',
        'tab_all':          'все',
        'no_cats':          'категорий нет',
        'no_data':          '// данных нет<br>запустите scan.sh',
        'no_results':       '// ничего не найдено<br>измените запрос или категорию',
        'empty_hint':       'наведите курсор на элемент в списке<br>чтобы увидеть подробности<br><br><span style="color:#6e4a00;font-size:11px;">клик или Enter — закрепить<br>Esc — снять закрепление<br>Ctrl+клик по категории — мультивыбор</span>',
        'chip_year':        'год',
        'chip_size':        'размер',
        'chip_language':    'язык',
        'chip_duration':    'длит.',
        'chip_version':     'версия',
        'chip_files':       'файлов',
        'section_desc':     'описание',
        'section_details':  'детали',
        'section_files':    'файлы',
        'section_shots':    'скриншоты',
        'desc_empty':       'описание отсутствует',
        'kv_developer':     'разработчик',
        'kv_publisher':     'издатель',
        'kv_director':      'режиссёр',
        'kv_series':        'серия',
        'kv_country':       'страна',
        'kv_comment':       'комментарий',
        'btn_copy':         'скопировать путь',
        'btn_back':         '← назад к списку',
        'toast_no_path':    'путь не указан',
        'toast_copied':     'скопировано: ',
        'toast_copy_fail':  'не удалось скопировать',
        'toast_android':    'Android не позволяет использовать пути к файлам на USB — ограничение системы',
        'toast_base_set':   'базовый путь: ',
        'toast_base_reset': 'базовый путь сброшен',
        'cat_games':        'Игры',
        'cat_movies':       'Фильмы',
        'cat_other':        'Прочее',
        'base_diag_title':  'Базовый путь — префикс, добавляемый к путям при копировании.',
        'base_diag_url':    'URL:',
        'base_diag_proto':  'Протокол:',
        'base_diag_mem':    'Память:',
        'base_diag_hash':   'Hash:',
        'base_diag_ls':     'localStorage:',
        'base_diag_auto':   'Авто (file):',
        'base_diag_hint':   'Ввести префикс вручную, например:\\n  Android: /storage/XXXX-XXXX/\\n  Linux:   /media/user/XXXX-XXXX/\\n\\nПусто = сбросить.',
        'base_title_active': 'Базовый путь: ',
        'base_title_click':  ' (клик — изменить)',
        'base_title_setup':  'Настроить базовый путь для копирования',
        'not_set':          '(не задан)',
        'empty':            '(пусто)',
        'none':             '(нет)',
        'ls_unavailable':   'НЕДОСТУПЕН',
        # --- таблица ---
        'table_col_name':   'Имя',
        'table_col_type':   'Тип',
        'table_col_path':   'Путь',
        'table_empty':      '*Нет данных*',
    },
    'en': {
        'title':            'Cold Archive',
        'search_placeholder': 'search...',
        'sort_name_asc':    'name ▲',
        'sort_name_desc':   'name ▼',
        'sort_year_desc':   'year ▼',
        'sort_year_asc':    'year ▲',
        'sort_size_desc':   'size ▼',
        'sort_size_asc':    'size ▲',
        'settings_title':   'Base path for copying',
        'counter_items':    'items',
        'counter_shown':    'shown',
        'tab_all':          'all',
        'no_cats':          'no categories',
        'no_data':          '// no data<br>run scan.sh',
        'no_results':       '// nothing found<br>change query or category',
        'empty_hint':       'hover an item in the list<br>to see details<br><br><span style="color:#6e4a00;font-size:11px;">click or Enter — pin<br>Esc — unpin<br>Ctrl+click category — multi-select</span>',
        'chip_year':        'year',
        'chip_size':        'size',
        'chip_language':    'language',
        'chip_duration':    'runtime',
        'chip_version':     'version',
        'chip_files':       'files',
        'section_desc':     'description',
        'section_details':  'details',
        'section_files':    'files',
        'section_shots':    'screenshots',
        'desc_empty':       'no description',
        'kv_developer':     'developer',
        'kv_publisher':     'publisher',
        'kv_director':      'director',
        'kv_series':        'series',
        'kv_country':       'country',
        'kv_comment':       'comment',
        'btn_copy':         'copy path',
        'btn_back':         '← back to list',
        'toast_no_path':    'no path',
        'toast_copied':     'copied: ',
        'toast_copy_fail':  'copy failed',
        'toast_android':    'Android does not allow paths to USB files — system limitation',
        'toast_base_set':   'base path: ',
        'toast_base_reset': 'base path reset',
        'cat_games':        'Games',
        'cat_movies':       'Movies',
        'cat_other':        'Other',
        'base_diag_title':  'Base path — prefix added to paths when copying.',
        'base_diag_url':    'URL:',
        'base_diag_proto':  'Protocol:',
        'base_diag_mem':    'Memory:',
        'base_diag_hash':   'Hash:',
        'base_diag_ls':     'localStorage:',
        'base_diag_auto':   'Auto (file):',
        'base_diag_hint':   'Enter a prefix manually, e.g.:\\n  Android: /storage/XXXX-XXXX/\\n  Linux:   /media/user/XXXX-XXXX/\\n\\nEmpty = reset.',
        'base_title_active': 'Base path: ',
        'base_title_click':  ' (click to change)',
        'base_title_setup':  'Set base path for copying',
        'not_set':          '(not set)',
        'empty':            '(empty)',
        'none':             '(none)',
        'ls_unavailable':   'UNAVAILABLE',
        # --- table ---
        'table_col_name':   'Name',
        'table_col_type':   'Type',
        'table_col_path':   'Path',
        'table_empty':      '*No data*',
    },
}


def apply_lang(tpl, lang):
    """Подставляет {{ключи}} в шаблон строками нужного языка."""
    strings = LANG_STRINGS.get(lang, LANG_STRINGS['ru'])
    for key, value in strings.items():
        tpl = tpl.replace('{{' + key + '}}', value)
    return tpl


# ---------- Helpers ----------
def human_size(n):
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f"{n:.2f} {unit}" if unit != 'B' else f"{int(n)} {unit}"
        n /= 1024
    return f"{n:.2f} PB"

def is_content(name):
    low = name.lower()
    return any(low.endswith(ext) for ext in CONTENT_EXTS)

def is_image(name):
    return name.lower().endswith(IMG_EXTS)

def rel(path, root):
    return os.path.relpath(path, root).replace('\\', '/')

def parse_year_from_name(name):
    m = re.search(r'\b(19\d{2}|20\d{2})\b', name)
    return m.group(1) if m else ''


# ---------- info.txt / info.json ----------
def parse_info_txt(path):
    content = None
    for enc in ('utf-8', 'utf-8-sig', 'cp1251'):
        try:
            with open(path, 'r', encoding=enc) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue
        except OSError:
            return {}
    if content is None:
        return {}
    data = {}
    for line in content.splitlines():
        m = re.match(r'^\s*([^:#]+?)\s*:\s*(.*)$', line)
        if not m:
            continue
        key = m.group(1).strip().lower()
        val = m.group(2).strip()
        if val and key in FIELD_MAP:
            data[FIELD_MAP[key]] = val
    return data

def parse_info_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
    except Exception as e:
        print(f"     ⚠  info.json не читается: {e}")
        return {}
    if not isinstance(raw, dict):
        return {}
    data = {}
    for k, v in raw.items():
        key = k.lower()
        if key in JSON_FIELDS and v not in (None, ''):
            data[key] = str(v).strip()
    return data


# ---------- info/ ----------
def ensure_info_dir(item_path, category, item_name, lang):
    info_dir = os.path.join(item_path, 'info')
    ss_dir = os.path.join(info_dir, 'screenshots')
    txt = os.path.join(info_dir, 'info.txt')
    created = False
    if not os.path.isdir(info_dir):
        try:
            os.makedirs(info_dir, exist_ok=True)
            os.makedirs(ss_dir, exist_ok=True)
            year = parse_year_from_name(item_name)
            if lang == 'en':
                tpl = """\
Title: {name}
Category: {category}
Genre: 
Year: {year}
Description: 
Comment: 
"""
            else:
                tpl = """\
Название: {name}
Категория: {category}
Жанр: 
Год: {year}
Описание: 
Комментарий: 
"""
            with open(txt, 'w', encoding='utf-8') as f:
                f.write(tpl.format(name=item_name, category=category, year=year))
            created = True
        except OSError as e:
            print(f"     ⚠  Не удалось создать info/: {e}")
    return info_dir, created


# ---------- Cleanup ----------
def cleanup_generated(root, thumbs_dir_name, output_path, table_name=TABLE_NAME):
    removed = []
    thumbs_dir = os.path.join(root, thumbs_dir_name)
    if os.path.isdir(thumbs_dir):
        try:
            shutil.rmtree(thumbs_dir)
            removed.append(rel(thumbs_dir, root) + '/')
        except OSError as e:
            print(f"⚠  Не удалось удалить {thumbs_dir}: {e}")
    if os.path.isfile(output_path):
        try:
            os.remove(output_path)
            removed.append(rel(output_path, root))
        except OSError as e:
            print(f"⚠  Не удалось удалить {output_path}: {e}")
    table_path = os.path.join(root, table_name)
    if os.path.isfile(table_path):
        try:
            os.remove(table_path)
            removed.append(rel(table_path, root))
        except OSError as e:
            print(f"⚠  Не удалось удалить {table_path}: {e}")
    return removed


# ---------- Image ----------
def _prepare_image(im):
    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
        im = im.convert('RGBA')
        bg = Image.new('RGB', im.size, (0, 0, 0))
        bg.paste(im, mask=im.split()[-1])
        return bg
    if im.mode != 'RGB':
        return im.convert('RGB')
    return im

def image_to_base64_fit(src, size, quality):
    if not PILLOW:
        return ''
    try:
        with Image.open(src) as im:
            im = _prepare_image(im)
            im = ImageOps.fit(im, size, method=_RESAMPLE, centering=(0.5, 0.5))
            buf = io.BytesIO()
            im.save(buf, 'JPEG', quality=quality, optimize=True)
            return 'data:image/jpeg;base64,' + base64.b64encode(
                buf.getvalue()).decode('ascii')
    except Exception as e:
        print(f"     ⚠  Не удалось нарезать {os.path.basename(src)}: {e}")
        return ''

def make_screenshot_thumb(src, dst, size, quality):
    if not PILLOW:
        return False
    try:
        with Image.open(src) as im:
            im = _prepare_image(im)
            im.thumbnail(size, _RESAMPLE)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            im.save(dst, 'JPEG', quality=quality, optimize=True)
        return True
    except Exception as e:
        print(f"     ⚠  Не удалось нарезать {os.path.basename(src)}: {e}")
        return False


# ---------- Collect ----------
def _has_content(path):
    try:
        return any(is_content(f) for f in os.listdir(path))
    except OSError:
        return False

def collect_candidates(root):
    candidates = []
    try:
        entries = sorted(os.listdir(root))
    except OSError as e:
        print(f"❌ Не читается корень {root}: {e}")
        return candidates
    found_categories = set()
    for entry in entries:
        full = os.path.join(root, entry)
        if not os.path.isdir(full) or entry in SKIP_NAMES or entry.startswith('.'):
            continue
        cat_key = entry.lower().strip()
        if cat_key not in CATEGORY_DIRS:
            print(f"  ⏭  Пропущено (не Игры/Фильмы/Прочее): {entry}")
            continue
        category = CATEGORY_DIRS[cat_key]
        found_categories.add(category)
        try:
            sub_entries = sorted(os.listdir(full))
        except OSError:
            continue
        for sub in sub_entries:
            sub_full = os.path.join(full, sub)
            if (not os.path.isdir(sub_full) or sub.startswith('.')
                    or sub in SKIP_NAMES):
                continue
            if _has_content(sub_full):
                candidates.append((sub_full, category))
    if not found_categories:
        print("⚠  В корне не найдено папок Игры/Фильмы/Прочее.")
    return candidates


# ---------- Process item ----------
def process_item(item_path, category, root, opts):
    folder_name = os.path.basename(item_path)
    info_dir, created = ensure_info_dir(item_path, category, folder_name, opts.lang)
    if created:
        print(f"     ℹ  Создана info/ для «{folder_name}»")

    info = {}
    json_file = os.path.join(info_dir, 'info.json')
    txt_file = os.path.join(info_dir, 'info.txt')
    if os.path.isfile(json_file):
        info = parse_info_json(json_file)
    if not info and os.path.isfile(txt_file):
        info = parse_info_txt(txt_file)

    item_name = info.get('name') or folder_name

    files = []
    total_bytes = 0
    try:
        entries = sorted(os.listdir(item_path))
    except OSError:
        entries = []
    for f in entries:
        f_full = os.path.join(item_path, f)
        if os.path.isfile(f_full) and is_content(f):
            sz = os.path.getsize(f_full)
            total_bytes += sz
            files.append({
                'file': f,
                'size_h': human_size(sz),
                'path': rel(f_full, root),
            })
    if not files:
        return None

    cover_src = ''
    for cn in COVER_NAMES:
        cp = os.path.join(info_dir, cn)
        if os.path.isfile(cp):
            cover_src = cp
            break
    cover_base64 = ''
    if cover_src and not opts.no_thumbs:
        cover_base64 = image_to_base64_fit(cover_src, opts.list_size, opts.quality)

    screenshots = []
    ss_src_dir = os.path.join(info_dir, 'screenshots')
    if os.path.isdir(ss_src_dir):
        try:
            ss_files = sorted(os.listdir(ss_src_dir))
        except OSError:
            ss_files = []
        for sf in ss_files:
            sp = os.path.join(ss_src_dir, sf)
            if not (os.path.isfile(sp) and is_image(sf)):
                continue
            thumb_rel = ''
            if PILLOW and not opts.no_thumbs:
                base = os.path.splitext(sf)[0]
                thumb_dst = os.path.join(
                    root, opts.thumbs_dir, category, folder_name,
                    'screenshots', base + '.thumb.jpg')
                if make_screenshot_thumb(sp, thumb_dst, opts.screenshot_size, opts.quality):
                    thumb_rel = rel(thumb_dst, root)
            screenshots.append({
                'full': rel(sp, root),
                'thumb': thumb_rel,
            })

    item = {
        'name': item_name,
        'category': category,
        'folder_path': rel(item_path, root),
        'files': files,
        'path': files[0]['path'],
        'size': round(total_bytes / (1024 ** 3), 2),
        'size_h': human_size(total_bytes),
        'cover_base64': cover_base64,
        'screenshots': screenshots,
    }
    for field in ('description', 'genre', 'year', 'developer', 'publisher',
                  'director', 'language', 'version', 'series', 'country',
                  'duration', 'comment'):
        item[field] = info.get(field, '')
    return item


def build_search_index(item):
    cat = item.get('category', '')
    cat_extra = {
        'Игры':   'games game',
        'Фильмы': 'movies movie films',
        'Прочее': 'other misc',
    }.get(cat, '')
    parts = [
        item.get('name', ''), cat, cat_extra,
        item.get('genre', ''), item.get('description', ''),
        item.get('year', ''), item.get('developer', ''),
        item.get('publisher', ''), item.get('director', ''),
        item.get('series', ''), item.get('country', ''),
        item.get('language', ''), item.get('comment', ''),
    ]
    return ' '.join(p for p in parts if p).lower()


# ---------- generate_index_html ----------
def generate_index_html(script_dir, target_root, payload, lang='ru'):
    tpl_path = os.path.join(script_dir, TEMPLATE_NAME)
    dst = os.path.join(target_root, 'index.html')

    if not os.path.isfile(tpl_path):
        print(f"❌ Шаблон не найден: {tpl_path}")
        return False
    try:
        with open(tpl_path, 'r', encoding='utf-8') as f:
            tpl = f.read()
    except OSError as e:
        print(f"❌ Не удалось прочитать шаблон: {e}")
        return False

    marker = 'window.ARCHIVE_DATA = __ARCHIVE_DATA__;'
    if marker not in tpl:
        print(f"❌ В шаблоне нет маркера: {marker}")
        return False

    tpl = apply_lang(tpl, lang)

    data_json = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    data_json = data_json.replace('</', '<\\/')
    replacement = 'window.ARCHIVE_DATA = ' + data_json + ';'
    html = tpl.replace(marker, replacement, 1)

    if '__ARCHIVE_DATA__' in html:
        print("❌ После подстановки остался __ARCHIVE_DATA__")
        return False

    try:
        with open(dst, 'w', encoding='utf-8') as f:
            f.write(html)
    except OSError as e:
        print(f"❌ Не удалось записать index.html: {e}")
        return False

    sz = os.path.getsize(dst)
    print(f"📄 index.html → {dst} ({human_size(sz)})")
    return True


# ---------- generate_table ----------
def _md_escape_cell(s):
    """Экранирует pipe и переносы строк для markdown-таблицы."""
    if s is None:
        return ''
    return (str(s)
            .replace('\\', '\\\\')
            .replace('|', '\\|')
            .replace('\r', ' ')
            .replace('\n', ' '))


def generate_table(script_dir, target_root, items, lang='ru', title='', label='', table_name=TABLE_NAME):
    """Создаёт markdown-таблицу catalog.md: Имя | Тип | Путь."""
    strings = LANG_STRINGS.get(lang, LANG_STRINGS['ru'])
    dst = os.path.join(target_root, table_name)

    # Сортировка: сначала по категории (Игры → Фильмы → Прочее), потом по имени
    def sort_key(it):
        cat = it.get('category', '')
        return (CATEGORY_ORDER.get(cat, 99),
                (it.get('name') or '').lower())

    sorted_items = sorted(items, key=sort_key)

    lines = []
    header_title = title or strings['title']
    if label:
        lines.append(f"# {header_title} — {label}")
    else:
        lines.append(f"# {header_title}")
    lines.append('')

    if not sorted_items:
        lines.append(strings['table_empty'])
    else:
        col_name = strings['table_col_name']
        col_type = strings['table_col_type']
        col_path = strings['table_col_path']

        lines.append(f"| {col_name} | {col_type} | {col_path} |")
        lines.append("|------|------|------|")

        for it in sorted_items:
            folder_path = it.get('folder_path', '')
            # Имя — реальное имя папки на диске (а не info.name)
            folder_name = folder_path.rsplit('/', 1)[-1] if folder_path else it.get('name', '')
            # Тип — реальное имя группирующей папки на диске (Игры / фильмы / Games …)
            type_name = folder_path.split('/', 1)[0] if '/' in folder_path else ''
            # Путь — полный относительный путь от корня носителя
            rel_path = folder_path

            lines.append(
                "| " + _md_escape_cell(folder_name) +
                " | " + _md_escape_cell(type_name) +
                " | " + _md_escape_cell(rel_path) +
                " |"
            )

    content = '\n'.join(lines) + '\n'

    try:
        with open(dst, 'w', encoding='utf-8') as f:
            f.write(content)
    except OSError as e:
        print(f"❌ Не удалось записать {table_name}: {e}")
        return False

    sz = os.path.getsize(dst)
    print(f"📋 {table_name} → {dst} ({human_size(sz)})")
    return True


# ---------- Main ----------
def parse_size(s):
    m = re.match(r'^\s*(\d+)\s*[xх]\s*(\d+)\s*$', s, re.IGNORECASE)
    if not m:
        raise argparse.ArgumentTypeError(f"Ожидается WxH, получено: {s}")
    return (int(m.group(1)), int(m.group(2)))


def main():
    ap = argparse.ArgumentParser(
        description='Сканер холодного архива v3.2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Структура носителя:
  <root>/Игры/<Игра>/<архив>
  <root>/Фильмы/<Фильм>/<видео>
  <root>/Прочее/<Элемент>/<файл>
""")
    ap.add_argument('--root', default=None)
    ap.add_argument('--label', default='')
    ap.add_argument('--title', default='')
    ap.add_argument('--output', default='index.html')
    ap.add_argument('--thumbs-dir', default='.archive_thumbs')
    ap.add_argument('--list-size', type=parse_size, default=(160, 213))
    ap.add_argument('--screenshot-size', type=parse_size, default=(320, 200))
    ap.add_argument('--quality', type=int, default=72)
    ap.add_argument('--no-thumbs', action='store_true')
    ap.add_argument('--no-table', action='store_true',
                    help='Не создавать catalog.md')
    ap.add_argument('--keep-old', '--no-cleanup', dest='keep_old',
                    action='store_true')
    ap.add_argument('--lang', choices=['ru', 'en'], default='ru',
                    help='Язык интерфейса (по умолч. ru)')
    args = ap.parse_args()

    root = args.root or os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(root)

    if not os.path.isdir(root):
        print(f"❌ Не папка: {root}")
        sys.exit(1)
    if not os.access(root, os.W_OK):
        print(f"❌ Нет прав на запись в {root}")
        sys.exit(1)

    out_path = args.output
    if not os.path.isabs(out_path):
        out_path = os.path.join(root, out_path)

    title = args.title or LANG_STRINGS[args.lang]['title']

    print("🎮📼 Сканер холодного архива v3.2")
    print(f"📂 Корень:     {root}")
    print(f"🏷  Метка:      {args.label or '(без метки)'}")
    print(f"🌐 Язык:       {args.lang}")
    print(f"📄 Файл:       {out_path}")
    if not args.no_table:
        print(f"📋 Таблица:    {os.path.join(root, TABLE_NAME)}")
    print(f"🖼  Скриншоты:  {os.path.join(root, args.thumbs_dir)}/")
    if not PILLOW:
        print("⚠  Pillow не установлен — превью и обложки будут пустыми.")
        print("   Установите: python3 -m pip install Pillow")
    print()

    if not args.keep_old:
        removed = cleanup_generated(root, args.thumbs_dir, out_path)
        if removed:
            print("🧹 Удалено старое:")
            for r in removed:
                print(f"   - {r}")
            print()
        else:
            print("🧹 Старых данных нет")
            print()

    print("🔍 Поиск элементов…")
    candidates = collect_candidates(root)
    total = len(candidates)
    print(f"   Найдено: {total}")
    print()

    script_dir = os.path.dirname(os.path.abspath(__file__))

    if total == 0:
        print("😔 Ничего не найдено. Проверьте структуру:")
        print("   <root>/Игры/<Игра>/<архив>")
        print("   <root>/Фильмы/<Фильм>/<видео>")
        print("   <root>/Прочее/<Элемент>/<файл>")
        payload = {
            'schema_version': SCHEMA_VERSION,
            'generated': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'title': title, 'label': args.label,
            'root': root, 'count': 0, 'items': [],
            'lang': args.lang,
        }
        generate_index_html(script_dir, root, payload, args.lang)
        if not args.no_table:
            generate_table(script_dir, root, [], args.lang, title, args.label)
        return

    items = []
    errors = 0
    for i, (item_path, category) in enumerate(candidates, 1):
        prefix = f"  [{i:>3}/{total}]"
        print(f"{prefix} [{category}] {os.path.basename(item_path)}")
        try:
            item = process_item(item_path, category, root, args)
        except Exception as e:
            print(f"        ❌ Ошибка: {e}")
            errors += 1
            continue
        if item is None:
            print(f"        ⏭  Пропущен (нет файлов)")
            continue
        item['search_index'] = build_search_index(item)
        items.append(item)

    payload = {
        'schema_version': SCHEMA_VERSION,
        'generated': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'title': title,
        'label': args.label,
        'root': root,
        'count': len(items),
        'items': items,
        'lang': args.lang,
    }
    ok = generate_index_html(script_dir, root, payload, args.lang)
    if not args.no_table:
        generate_table(script_dir, root, items, args.lang, title, args.label)

    print()
    print(f"✅ Готово: {len(items)} элементов")
    if errors:
        print(f"⚠  Ошибок: {errors}")
    if not ok:
        sys.exit(1)

    if PILLOW and not args.no_thumbs:
        thumbs_dir = os.path.join(root, args.thumbs_dir)
        if os.path.isdir(thumbs_dir):
            cnt = 0
            for _r, _d, files in os.walk(thumbs_dir):
                cnt += len(files)
            if cnt:
                print(f"🖼  Скриншоты: {cnt} файлов в {args.thumbs_dir}/")

    by_cat = {}
    for it in items:
        by_cat.setdefault(it['category'], []).append(it)
    if by_cat:
        print()
        print("📊 По категориям:")
        for cat in sorted(by_cat):
            print(f"   {cat}: {len(by_cat[cat])}")


if __name__ == '__main__':
    main()