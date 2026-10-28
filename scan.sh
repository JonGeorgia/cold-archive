#!/bin/bash
# ============================================================
# scan.sh — сканер холодного архива с выбором носителя и языка
# ============================================================
#   ./scan.sh                                 # меню + язык
#   ./scan.sh --root /mnt/hdd3 --lang en      # скриптовый режим
#   ./scan.sh --keep-open                     # пауза в конце (отладка)
# ============================================================

# ---------- Логирование ----------
# Лог создаётся ВСЕГДА. Но: глобальный "exec > >(tee ...)" НЕ используем —
# при запуске из файлового менеджера pty может быть закрыт до завершения
# scan.py, что даёт SIGPIPE и убивает сканирование.
LOG_FILE="/tmp/scan-$(date +%Y%m%d-%H%M%S).log"
: > "$LOG_FILE"
echo "📋 Лог: $LOG_FILE"
echo ""

# ---------- TTY? ----------
# -t 0 && -t 1 — «настоящий» терминал. Файловый менеджер с pty тоже даст true,
# но pty может быть закрыт менеджером. Дополнительно считаем, что мы «под
# менеджером», если переменная окружения запущена из Nautilus/Nemo/Thunar.
if [ -t 0 ] && [ -t 1 ] && [ -z "${NAUTILUS_SCRIPT_SELECTED_FILE_PATHS:-}" ] && [ -z "${NEMO_SCRIPT_SELECTED_FILE_PATHS:-}" ]; then
    NO_TTY=0
else
    NO_TTY=1
fi

# ---------- Уведомления (zenity) — синхронно ----------
# Синхронно (без &), чтобы окно точно показалось, даже если pty закрыт.
# При ошибке — окно с ошибкой, при успехе — окно с результатом.
notify_info() {
    if command -v zenity >/dev/null && [ -n "${DISPLAY:-}" ]; then
        local text="$1"
        [ -n "$LOG_FILE" ] && text="$text

Лог: $LOG_FILE"
        zenity --info --title="Холодный архив" --text="$text" --timeout=20
    fi
}
notify_error() {
    if command -v zenity >/dev/null && [ -n "${DISPLAY:-}" ]; then
        local text="$1"
        [ -n "$LOG_FILE" ] && text="$text

Лог: $LOG_FILE"
        zenity --error --title="Холодный архив" --text="$text" --timeout=90
    fi
}

# ---------- UTF-8 локаль для GUI ----------
if locale -a 2>/dev/null | grep -qix 'C\.utf-\?8'; then
    export LC_ALL=C.UTF-8; export LANG=C.UTF-8
elif locale -a 2>/dev/null | grep -qix 'en_US\.utf-\?8'; then
    export LC_ALL=en_US.UTF-8; export LANG=en_US.UTF-8
elif locale -a 2>/dev/null | grep -qix 'ru_RU\.utf-\?8'; then
    export LC_ALL=ru_RU.UTF-8; export LANG=ru_RU.UTF-8
else
    echo "⚠  UTF-8 локаль не найдена — GUI-диалоги могут не работать."
fi
export NO_AT_BRIDGE=1 2>/dev/null || true

# ---------- Проверки ----------
if ! command -v python3 >/dev/null; then
    echo "❌ Python 3 не найден. Установите: sudo apt install python3"
    notify_error "Python 3 не найден. Установите: sudo apt install python3"
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || {
    echo "❌ Не удалось перейти в $SCRIPT_DIR"
    notify_error "Не удалось перейти в папку скрипта: $SCRIPT_DIR"
    exit 1
}

if [ ! -f "$SCRIPT_DIR/scan.py" ]; then
    echo "❌ scan.py не найден рядом с scan.sh ($SCRIPT_DIR)"
    notify_error "scan.py не найден рядом с scan.sh"
    exit 1
fi
if [ ! -f "$SCRIPT_DIR/index_template.html" ]; then
    echo "❌ index_template.html не найден рядом со сканером"
    notify_error "index_template.html не найден рядом со сканером"
    exit 1
fi
if ! python3 -c "import PIL" 2>/dev/null; then
    echo "⚠  Pillow не установлен — обложки и превью не будут созданы."
    echo "   Для полноценной работы: python3 -m pip install Pillow"
    echo ""
fi

# ---------- Аргументы ----------
ROOT=""; LABEL=""; TITLE=""; OUTPUT=""; LANG=""
NO_MENU=0; OPEN_BROWSER=1; KEEP_OPEN=0

need_arg() {
    if [ $# -lt 2 ] || [ -z "$2" ]; then
        echo "❌ Опция $1 требует аргумент (см. --help)"
        exit 1
    fi
}

while [ $# -gt 0 ]; do
    case "$1" in
        --root)       need_arg "$1" "$2"; ROOT="$2"; shift 2 ;;
        --label)      need_arg "$1" "$2"; LABEL="$2"; shift 2 ;;
        --title)      need_arg "$1" "$2"; TITLE="$2"; shift 2 ;;
        --output)     need_arg "$1" "$2"; OUTPUT="$2"; shift 2 ;;
        --lang)       need_arg "$1" "$2"; LANG="$2"; shift 2 ;;
        --no-menu)    NO_MENU=1; shift ;;
        --no-open)    OPEN_BROWSER=0; shift ;;
        --keep-open)  KEEP_OPEN=1; shift ;;
        -h|--help)
            cat <<'EOF'
Использование: ./scan.sh [опции]

  --root PATH      Сканировать PATH (без меню выбора носителя)
  --label NAME     Метка носителя (для отображения)
  --title TITLE    Заголовок каталога
  --output FILE    Имя выходного файла (по умолч. index.html)
  --lang ru|en     Язык интерфейса каталога (по умолч. ru)
  --no-menu        Не показывать меню (ни носитель, ни язык)
  --no-open        Не открывать браузер после сканирования
  --keep-open      Пауза в конце (только при запуске из терминала)
  -h, --help       Эта справка

Структура носителя:
  <root>/Игры/<Игра>/<архив>
  <root>/Фильмы/<Фильм>/<видео>
  <root>/Прочее/<Элемент>/<файл>

Результат: один index.html со вшитыми данными и base64-обложками.
Лог пишется ВСЕГДА: /tmp/scan-YYYYMMDD-HHMMSS.log
EOF
            exit 0 ;;
        *) echo "Неизвестный аргумент: $1 (см. --help)"; exit 1 ;;
    esac
done

# ---------- Определение носителей ----------
detect_targets() {
    python3 - <<'PYEOF'
import json, subprocess
try:
    data = json.loads(subprocess.check_output(
        ['lsblk', '-J', '-o', 'NAME,LABEL,SIZE,MOUNTPOINT,TYPE,RM,FSTYPE'],
        stderr=subprocess.DEVNULL))
except Exception:
    data = {'blockdevices': []}

seen = set()
def walk(dev):
    mp = dev.get('mountpoint'); typ = dev.get('type', '')
    fstype = (dev.get('fstype') or '').lower()
    if mp and typ in ('part', 'disk', 'loop') and fstype not in ('swap', 'squashfs', ''):
        if mp not in seen:
            seen.add(mp)
            print(f"{mp}\t{dev.get('label') or ''}\t{dev.get('size') or ''}\t"
                  f"{'removable' if dev.get('rm') else 'fixed'}")
    for c in dev.get('children') or []:
        walk(c)

for d in data.get('blockdevices', []):
    walk(d)
PYEOF
    for d in /media/*/* /run/media/*/* /mnt/* /Volumes/*; do
        [ -d "$d" ] && [ -r "$d" ] || continue
        case "$d" in /mnt/*) [ -z "$(ls -A "$d" 2>/dev/null)" ] && continue ;; esac
        printf '%s\t\t\tfolder\n' "$d"
    done
}

# ---------- Выбор вручную ----------
choose_other() {
    if command -v zenity >/dev/null && [ -n "${DISPLAY:-}" ]; then
        local d rc
        d=$(zenity --file-selection --directory \
             --title="Выберите папку для сканирования" 2>/dev/null)
        rc=$?
        if [ $rc -eq 0 ] && [ -n "$d" ]; then echo "$d"; return 0; fi
        if [ $rc -eq 1 ]; then return 1; fi
        echo "⚠  zenity file-selection не сработал (код $rc) — ручной ввод" >&2
    fi
    echo -n "Путь к папке: " >&2
    local d
    read -r d
    [ -z "$d" ] && return 1
    if [ ! -d "$d" ]; then
        echo "❌ Не папка: $d" >&2
        return 1
    fi
    echo "$d"
}

# ---------- Меню выбора носителя ----------
show_menu() {
    local -a mps=() labels=() sizes=() kinds=()
    local -A seen=()
    while IFS=$'\t' read -r mp label size kind; do
        [ -z "$mp" ] && continue
        case "$mp" in
            /|/boot|/boot/efi|/home|/var|/usr|/proc|/sys|/dev|/run|/snap) continue ;;
        esac
        [ -n "${seen[$mp]:-}" ] && continue
        seen[$mp]=1
        mps+=("$mp"); labels+=("${label:-—}"); sizes+=("${size:-?}"); kinds+=("$kind")
    done < <(detect_targets)
    local n=${#mps[@]}

    if command -v zenity >/dev/null && [ -n "${DISPLAY:-}" ]; then
        local args=() i=0
        while [ $i -lt $n ]; do
            args+=("${mps[$i]}" "${labels[$i]}" "${sizes[$i]}" "${kinds[$i]}")
            i=$((i+1))
        done
        args+=("__OTHER__" "Выбрать вручную…" "" "")
        local out rc
        out=$(zenity --list \
            --title="🎮📼 Холодный архив — выбор носителя" \
            --text="Куда сканировать и куда положить каталог:" \
            --column="Путь" --column="Метка" --column="Размер" --column="Тип" \
            --print-column=1 --height=500 --width=900 \
            "${args[@]}" 2>/dev/null)
        rc=$?
        if [ $rc -eq 0 ] && [ -n "$out" ]; then
            if [ "$out" = "__OTHER__" ]; then choose_other; return $?; fi
            echo "$out"; return 0
        fi
        if [ $rc -eq 1 ]; then echo "Отменено." >&2; return 1; fi
        echo "⚠  zenity не сработал (код $rc) — пробую другой способ…" >&2
    fi

    if command -v whiptail >/dev/null; then
        local args=() i=0
        while [ $i -lt $n ]; do
            local emoji=""
            case "${kinds[$i]}" in
                removable) emoji="🔌 " ;;
                fixed)     emoji="💾 " ;;
                folder)    emoji="📁 " ;;
            esac
            args+=("${mps[$i]}" "${emoji}${labels[$i]} (${sizes[$i]})")
            i=$((i+1))
        done
        args+=("__OTHER__" "📂 Выбрать вручную…")
        local out rc
        out=$(whiptail --title "Холодный архив — выбор носителя" \
            --menu "Куда сканировать и куда положить каталог:" \
            22 100 12 "${args[@]}" 3>&1 1>&2 2>&3)
        rc=$?
        if [ $rc -eq 0 ] && [ -n "$out" ]; then
            if [ "$out" = "__OTHER__" ]; then choose_other; return $?; fi
            echo "$out"; return 0
        fi
        if [ $rc -eq 1 ]; then echo "Отменено." >&2; return 1; fi
        echo "⚠  whiptail не сработал (код $rc) — пробую другой способ…" >&2
    fi

    if command -v dialog >/dev/null; then
        local args=() i=0
        while [ $i -lt $n ]; do
            args+=("${mps[$i]}" "${labels[$i]} (${sizes[$i]})")
            i=$((i+1))
        done
        args+=("__OTHER__" "Выбрать вручную…")
        local out rc
        out=$(dialog --stdout --title "Холодный архив" \
            --menu "Выберите носитель:" 22 100 12 "${args[@]}")
        rc=$?
        if [ $rc -eq 0 ] && [ -n "$out" ]; then
            if [ "$out" = "__OTHER__" ]; then choose_other; return $?; fi
            echo "$out"; return 0
        fi
        if [ $rc -eq 1 ]; then echo "Отменено." >&2; return 1; fi
        echo "⚠  dialog не сработал (код $rc) — пробую терминал…" >&2
    fi

    if [ "$NO_TTY" -eq 1 ]; then
        echo "ℹ  Нет TTY — использую папку скрипта: $SCRIPT_DIR" >&2
        echo "$SCRIPT_DIR"
        return 0
    fi

    echo "" >&2
    echo "Доступные носители:" >&2
    local i=0
    while [ $i -lt $n ]; do
        printf "  %d) %s (%s) — %s\n" $((i+1)) "${labels[$i]}" "${sizes[$i]}" "${mps[$i]}" >&2
        i=$((i+1))
    done
    printf "  %d) Выбрать вручную…\n" $((n+1)) >&2
    echo "" >&2
    local reply
    while :; do
        printf "Номер (Enter — отмена): " >&2
        read -r reply
        [ -z "$reply" ] && return 1
        [[ "$reply" =~ ^[0-9]+$ ]] || { echo "Введите число" >&2; continue; }
        if [ "$reply" -ge 1 ] && [ "$reply" -le $n ]; then
            echo "${mps[$((reply-1))]}"; return 0
        elif [ "$reply" -eq $((n+1)) ]; then
            choose_other; return $?
        fi
        echo "Нет такого номера" >&2
    done
}

# ---------- Выбор языка ----------
ask_lang() {
    if command -v zenity >/dev/null && [ -n "${DISPLAY:-}" ]; then
        local out rc
        out=$(zenity --list \
            --title="🎮📼 Холодный архив — язык" \
            --text="Выберите язык интерфейса каталога" \
            --column="Код" --column="Язык" \
            --print-column=1 --height=320 --width=460 \
            "ru" "Русский" \
            "en" "English" 2>/dev/null)
        rc=$?
        if [ $rc -eq 0 ] && [ -n "$out" ]; then echo "$out"; return 0; fi
        if [ $rc -eq 1 ]; then return 1; fi
        echo "⚠  zenity (язык) не сработал (код $rc) — пробую другой способ…" >&2
    fi

    if command -v whiptail >/dev/null; then
        local out rc
        out=$(whiptail --title "Холодный архив — язык" \
            --menu "Выберите язык интерфейса каталога:" \
            16 76 4 \
            "ru" "Русский" \
            "en" "English" 3>&1 1>&2 2>&3)
        rc=$?
        if [ $rc -eq 0 ] && [ -n "$out" ]; then echo "$out"; return 0; fi
        if [ $rc -eq 1 ]; then return 1; fi
        echo "⚠  whiptail (язык) не сработал (код $rc) — пробую другой способ…" >&2
    fi

    if command -v dialog >/dev/null; then
        local out rc
        out=$(dialog --stdout --title "Холодный архив — язык" \
            --menu "Выберите язык интерфейса каталога:" 16 76 4 \
            "ru" "Русский" \
            "en" "English")
        rc=$?
        if [ $rc -eq 0 ] && [ -n "$out" ]; then echo "$out"; return 0; fi
        if [ $rc -eq 1 ]; then return 1; fi
        echo "⚠  dialog (язык) не сработал (код $rc) — пробую терминал…" >&2
    fi

    if [ "$NO_TTY" -eq 1 ]; then
        echo "ℹ  Нет TTY — беру RU" >&2
        echo "ru"
        return 0
    fi

    echo "" >&2
    echo "Язык интерфейса каталога:" >&2
    echo "  1) Русский (RU)" >&2
    echo "  2) English (EN)" >&2
    echo "" >&2
    local reply
    while :; do
        printf "Номер (Enter — RU по умолчанию): " >&2
        read -r reply
        [ -z "$reply" ] && { echo "ru"; return 0; }
        case "$reply" in
            1|ru|RU|Ru) echo "ru"; return 0 ;;
            2|en|EN|En) echo "en"; return 0 ;;
            *) echo "Введите 1 или 2" >&2 ;;
        esac
    done
}

# ---------- Основная логика ----------
echo "🎮📼 Сканер холодного архива"
echo "========================"
echo ""

if [ -z "$ROOT" ] && [ "$NO_MENU" -eq 0 ]; then
    ROOT=$(show_menu) || {
        echo "Отменено пользователем."
        notify_info "Сканирование отменено."
        exit 0
    }
fi

if [ -z "$ROOT" ]; then
    ROOT="$SCRIPT_DIR"
    echo "ℹ  Носитель не выбран — сканирую папку скрипта: $ROOT"
fi

if [ ! -d "$ROOT" ]; then
    echo "❌ Не папка: $ROOT"
    notify_error "Не папка: $ROOT"
    exit 1
fi
if [ ! -w "$ROOT" ]; then
    echo "❌ Нет прав на запись в $ROOT"
    notify_error "Нет прав на запись в $ROOT"
    exit 1
fi

if [ -z "$LANG" ]; then
    if [ "$NO_MENU" -eq 1 ]; then
        LANG="ru"
    else
        LANG=$(ask_lang) || {
            echo "Отменено пользователем."
            notify_info "Сканирование отменено."
            exit 0
        }
    fi
fi

if [ -z "$LABEL" ]; then
    LABEL=$(findmnt -n -o LABEL --target "$ROOT" 2>/dev/null | head -1)
    [ -z "$LABEL" ] && LABEL=$(basename "$ROOT")
fi

[ -z "$OUTPUT" ] && OUTPUT="index.html"
case "$OUTPUT" in
    /*) OUT_PATH="$OUTPUT" ;;
    *)  OUT_PATH="$ROOT/$OUTPUT" ;;
esac

echo "📂 Сканирую: $ROOT"
echo "🏷  Метка:    $LABEL"
echo "🌐 Язык:     $LANG"
echo ""

# Записать шапку в лог (для диагностики)
{
    echo "=== scan.sh $(date) ==="
    echo "PWD:     $(pwd)"
    echo "ROOT:    $ROOT"
    echo "LABEL:   $LABEL"
    echo "LANG:    $LANG"
    echo "OUTPUT:  $OUT_PATH"
    echo "NO_TTY:  $NO_TTY"
    echo ""
} >> "$LOG_FILE"

SCAN_ARGS=(--root "$ROOT" --output "$OUT_PATH" --label "$LABEL" --lang "$LANG")
[ -n "$TITLE" ] && SCAN_ARGS+=(--title "$TITLE")

# ---------- Запуск scan.py ----------
# КЛЮЧЕВОЙ момент: если нет «настоящего» TTY (или pty может закрыться),
# пишем scan.py ТОЛЬКО в файл. Иначе tee/pty могут убить процесс SIGPIPE.
if [ "$NO_TTY" -eq 0 ]; then
    # Терминал: показываем прогресс в консоли, лог — только шапка
    python3 "$SCRIPT_DIR/scan.py" "${SCAN_ARGS[@]}"
    STATUS=$?
else
    # Менеджер: тихо в лог, pty можно закрывать безопасно
    echo "▶ запуск scan.py (вывод в лог)" >> "$LOG_FILE"
    python3 "$SCRIPT_DIR/scan.py" "${SCAN_ARGS[@]}" >> "$LOG_FILE" 2>&1
    STATUS=$?
fi
echo "=== exit $STATUS $(date) ===" >> "$LOG_FILE"

# ---------- Ошибка ----------
if [ $STATUS -ne 0 ]; then
    echo ""
    echo "❌ Сканирование прервано (код $STATUS)"
    echo "📋 Лог: $LOG_FILE"

    if [ "$NO_TTY" -eq 1 ] && [ -f "$LOG_FILE" ]; then
        echo ""
        echo "--- последние 30 строк лога ---"
        tail -n 30 "$LOG_FILE"
        echo "------------------------------"
    fi

    notify_error "Сканирование прервано (код $STATUS).

$([ -f "$OUT_PATH" ] && echo "index.html: $OUT_PATH" || echo "index.html не создан")"

    if command -v xdg-open >/dev/null && [ -n "${DISPLAY:-}" ] && [ -f "$LOG_FILE" ]; then
        xdg-open "$LOG_FILE" >/dev/null 2>&1 &
    fi

    if [ "$KEEP_OPEN" -eq 1 ] && [ "$NO_TTY" -eq 0 ]; then
        echo ""
        read -p "Нажмите Enter для выхода..."
    fi
    exit $STATUS
fi

# ---------- Успех ----------
if [ "$OPEN_BROWSER" -eq 1 ] && [ -f "$OUT_PATH" ]; then
    URL="file://$OUT_PATH"
    echo ""
    echo "🌐 Открываю: $URL"
    for b in xdg-open firefox google-chrome chromium chromium-browser \
             microsoft-edge open; do
        if command -v "$b" >/dev/null; then
            "$b" "$URL" >/dev/null 2>&1 &
            break
        fi
    done
fi

notify_info "Готово.

$OUT_PATH"

if [ "$KEEP_OPEN" -eq 1 ] && [ "$NO_TTY" -eq 0 ]; then
    echo ""
    read -p "Нажмите Enter для выхода..."
fi

exit 0