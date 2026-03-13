# Document Parser

Парсинг HTML/Markdown документов в структурированный YAML с ID-нумерацией блоков.

## Возможности

| Компонент | Описание |
|---|---|
| `structurizer.py` | HTML/Markdown → AST → структурированный YAML с иерархическими ID |
| `text_extractor.py` | Извлечение текста из YAML по диапазону ID |
| `links_extractor.py` | Извлечение ссылок и изображений из YAML |
| `utils.py` | Проверка последовательности ID, вывод всех ID |

## Установка

```bash
pip install -e .
```

## CLI

```bash
python -m document_parser --help
```

### Парсинг CSV с HTML-статьями

```bash
# Базовый запуск
python -m document_parser parse-csv -f articles.csv

# Указать колонку и выходную директорию
python -m document_parser parse-csv -f data.csv --html-column body_html --output-dir output/
```

### Парсинг Markdown

```bash
python -m document_parser parse-md -f note.md
python -m document_parser parse-md -f README.md --output-dir output/
```

### Извлечение текста по ID

```bash
# Один блок с дочерними
python -m document_parser extract-text -f parsed_yaml/986380.yaml -s 4.1

# Диапазон блоков
python -m document_parser extract-text -f parsed_yaml/986380.yaml -s 4 -e 4.1.1.2
```

### Извлечение ссылок и изображений

```bash
# Один файл
python -m document_parser extract-assets -f parsed_yaml/986380.yaml

# Все файлы из output_dir
python -m document_parser extract-assets
```

### Список ID блоков

```bash
python -m document_parser list-ids -f parsed_yaml/986380.yaml
```

### Проверка последовательности ID

```bash
# Один файл
python -m document_parser check-ids -f parsed_yaml/986380.yaml

# Все файлы
python -m document_parser check-ids
```

### Утилиты конфигурации

```bash
# Валидация конфигурации
python -m document_parser validate

# Показать итоговый конфиг
python -m document_parser show-config
```

## Конфигурация

Файл `conf/config.yaml`:

```yaml
output_dir: parsed_yaml     # Директория для YAML-результатов
input_file: null             # Входной файл
html_column: content_html    # Колонка с HTML в CSV
assets_dir: assets           # Директория для images/links
log_level: INFO
```

Переопределение через CLI:

```bash
python -m document_parser parse-csv -f data.csv -o "html_column=body_html"
```

## Программный API

```python
from document_parser import (
    process_csv,          # CSV → YAML
    process_md_file,      # Markdown → YAML
    extract_from_yaml,    # YAML → текст по ID
    collect_assets,       # document → (images, links)
    check_id_sequence,    # проверка ID
)
```
