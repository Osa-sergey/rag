# RAPTOR Knowledge Graph Pipeline

Система для продвинутого RAG (Retrieval-Augmented Generation), объединяющая иерархическую суммаризацию текста (RAPTOR) и построение Графа Знаний (Knowledge Graph) в Neo4j.

## 🚀 Быстрый старт

### 1. Предварительные требования
- **Python 3.10+**
- **Docker & Docker Compose**
- **uv** (рекомендуется для управления зависимостями)

### 2. Развертывание инфраструктуры
Запустите векторную базу данных Qdrant и графовую базу Neo4j:
```powershell
docker-compose up -d
```
- Qdrant Dashboard: `http://localhost:6333/dashboard`
- Neo4j Browser: `http://localhost:7474` (логин/пароль по умолчанию: `neo4j/password`)

### 3. Установка зависимостей
С помощью `uv`:
```powershell
uv venv
.venv\Scripts\activate
uv pip install -e .
```

### 4. Настройка конфигурации
Отредактируйте `raptor_pipeline/conf/config.yaml`. Основные параметры:
- `embeddings`: выберите провайдера (`openai`, `deepseek` или `ollama`).
- `api_key`: укажите ваш ключ (или значение в соответствующих под-конфигах в `conf/embeddings/`).

### 5. Запуск пайплайна
Положите ваши YAML документы (результат парсинга) в папку `parsed_yaml/` и запустите:
```powershell
python -m raptor_pipeline.main
```
Пайплайн выполнит:
1. Гибридное чанкирование (с сохранением контекста заголовков).
2. Построение дерева суммаризаций (RAPTOR).
3. Глобальную дедупликацию ключевых слов.
4. Экстракцию связей и сохранение в Neo4j и Qdrant.

---

## 🔍 Инструменты визуализации и отладки

### Просмотр дерева чанков и саммари (Qdrant + Neo4j)
Показывает иерархию суммаризаций и **общее саммари статьи**:
```powershell
# Дерево для конкретной статьи (краткий вывод)
python -m raptor_pipeline.inspect_tree article_id="название_статьи"

# С полным текстом узлов
python -m raptor_pipeline.inspect_tree article_id="название_статьи" full_text=true

# Все статьи
python -m raptor_pipeline.inspect_tree
```
В конце вывода отображается **общее саммари статьи** из Neo4j.

### Инспекция графа знаний (Neo4j + Qdrant)
Связи группируются по **исходному чанку** — видно, откуда именно взялась каждая связь:
```powershell
# Список всех ключевых слов
python -m raptor_pipeline.inspect_graph

# Исследовать конкретный термин (связи + исходные тексты)
python -m raptor_pipeline.inspect_graph word="rag"

# Кириллица поддерживается без кавычек
python -m raptor_pipeline.inspect_graph word=оптимизация
```
Для каждого термина показываются:
- Связи, сгруппированные по source chunk с исходным текстом
- Статьи, содержащие ключевое слово
- Перекрёстные ссылки между статьями (с указанием chunk-источника)

### Сброс данных
Если нужно начать с чистого листа:
```powershell
python -m raptor_pipeline.reset_stores
```

## 📊 Topic Modeler — кросс-статейное тематическое моделирование

Отдельная утилита для обнаружения тем (BERTopic) и обогащения Article-нод метаданными.

### Обучение на всех статьях
```powershell
python -m topic_modeler mode=train
```
Загружает тексты из `parsed_yaml/`, метаданные из `data/row_data/scrapped_articles*.csv`,
обучает BERTopic, создаёт `:Topic` ноды и `[:BELONGS_TO_TOPIC]` связи в Neo4j.

### Добавить одну статью (инференс)
```powershell
python -m topic_modeler mode=add_article article_path=parsed_yaml/957000_20260204_130209.yaml
```

### Конфигурация
Каждый суб-компонент BERTopic настраивается через `topic_modeler/conf/config.yaml`:
- **UMAP**: `n_neighbors`, `n_components`, `min_dist`, `metric`
- **HDBSCAN**: `min_cluster_size`, `min_samples`, `metric`
- **Vectorizer**: `min_df`, `ngram_range`, `stop_words`
- **Representation**: KeyBERT, MMR (вкл/выкл + параметры)

## 🛠 Архитектура проекта
- `stores/`: Общий модуль хранения (Neo4j `graph_store`) — используется обоими пайплайнами.
- `topic_modeler/`: Standalone BERTopic утилита (train / add_article).
- `raptor_pipeline/chunker/`: Гибридный чанкер (Paragraph-aware + Semantic).
- `raptor_pipeline/knowledge_graph/`: Логика экстракции и **Refiner** (дедупликация).
- `raptor_pipeline/raptor/`: Рекурсивная кластеризация и суммаризация.
- `document_parser/`: Модули для обработки исходных YAML структур.
- `conf/prompts/`: Версионированные промпты для LLM.

---

## ⚡ llama.cpp — быстрый локальный LLM-бэкенд

**Зачем?** Ollama обрабатывает запросы последовательно (один за другим).
`llama-server` из llama.cpp поддерживает **continuous batching** — параллельную обработку
нескольких запросов в одном батче на GPU, что в разы быстрее для пайплайна.

### 1. Скачать llama.cpp

**Windows** — готовые бинарники:
```powershell
# Скачать последний релиз (выберите нужную архитектуру):
# https://github.com/ggml-org/llama.cpp/releases
# Например: llama-bXXXX-bin-win-cuda-cu12.4-x64.zip (для NVIDIA GPU)
# Распаковать в удобную директорию, например D:\tools\llama.cpp\
```

**Linux / macOS** — собрать из исходников:
```bash
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
cmake -B build -DGGML_CUDA=ON   # для NVIDIA GPU; без флага — CPU
cmake --build build --config Release -j
```

### 2. Скачать GGUF-модель

Модель `gemma-3-12b-it` в формате GGUF (квантование Q4_K_M — баланс скорости и качества):

```powershell
# Вариант A: через huggingface-cli
pip install huggingface-hub
huggingface-cli download bartowski/google_gemma-3-12b-it-GGUF \
    google_gemma-3-12b-it-Q4_K_M.gguf \
    --local-dir D:\models

# Вариант B: через браузер
# https://huggingface.co/bartowski/google_gemma-3-12b-it-GGUF
# Скачать файл google_gemma-3-12b-it-Q4_K_M.gguf
```

> **💡 Требования к памяти:** Q4_K_M ~7.5 GB VRAM. Для 8 GB карт подходит идеально.
> Для карт с 12+ GB можно использовать Q6_K или Q8_0 для лучшего качества.

### 3. Запустить llama-server

```powershell
# Базовый запуск (8 параллельных слотов, GPU):
D:\tools\llama.cpp\llama-server.exe `
    -m D:\models\google_gemma-3-12b-it-Q4_K_M.gguf `
    --port 8080 `
    -ngl 99 `
    --parallel 8 `
    -c 2048 `
    --cont-batching

# Пояснение флагов:
#   -m              путь к GGUF-модели
#   --port 8080     порт API (по умолчанию 8080)
#   -ngl 99         выгрузить все слои на GPU
#   --parallel 8    количество параллельных слотов (= max_concurrency пайплайна)
#   -c 2048        размер контекста (все слоты делят между собой)
#   --cont-batching включить continuous batching
```

Проверить что сервер работает:
```powershell
curl http://localhost:8080/health
# Ожидаемый ответ: {"status":"ok"}
```

### 4. Запустить пайплайн с llama.cpp

```powershell
# Только Knowledge Graph (ключевые слова + связи) через llama.cpp:
python -m raptor_pipeline.main knowledge_graph=llama_cpp

# Knowledge Graph + суммаризация через llama.cpp:
python -m raptor_pipeline.main knowledge_graph=llama_cpp summarizer=llama_cpp

# С настройкой параллелизма (должен совпадать с --parallel сервера):
python -m raptor_pipeline.main knowledge_graph=llama_cpp max_concurrency=8 batch_size=8
```

