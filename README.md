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

### Просмотр дерева чанков (Qdrant)
Позволяет увидеть иерархию суммаризаций для конкретной статьи:
```powershell
python -m raptor_pipeline.inspect_tree article_id="название_статьи" full_text=true
```

### Инспекция графа знаний (Neo4j + Qdrant)
Позволяет найти слово, увидеть его связи и **исходный текст** чанков:
```powershell
# Посмотреть список всех ключевых слов
python -m raptor_pipeline.inspect_graph

# Исследовать конкретный термин
python -m raptor_pipeline.inspect_graph word="rag"
```

### Сброс данных
Если нужно начать с чистого листа:
```powershell
python -m raptor_pipeline.reset_stores
```

## 🛠 Архитектура проекта
- `raptor_pipeline/chunker/`: Гибридный чанкер (Paragraph-aware + Semantic).
- `raptor_pipeline/knowledge_graph/`: Логика экстракции и **Refiner** (дедупликация).
- `raptor_pipeline/raptor/`: Рекурсивная кластеризация и суммаризация.
- `document_parser/`: Модули для обработки исходных YAML структур.
- `conf/prompts/`: Версионированные промпты для LLM.
