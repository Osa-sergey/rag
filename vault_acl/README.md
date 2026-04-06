# Vault Access Control List (ACL) Module

Модуль предоставляет гибкую систему управления доступом к файлам в хранилище (vault). Совмещает ролевую модель (RBAC) с детализированными исключениями для отдельных пользователей и путей.

## Основные возможности

* **Полный контроль операций:** Разграничение по битовым флагам: `READ`, `WRITE`, `DELETE`, `CREATE`, `ALL`.
* **Поддержка YAML политик:** Конфигурация доступа описывается простым и понятным YAML файлом, который легко версионировать через Git.
* **Glob-разрешения:** Поддержка паттерн-матчинга путей (например `daily/*.md`, `projects/secret/**`).
* **Гибкая система приоритетов:** Включает механизм разрешения коллизий между правилами на основе явных приоритетов, специфичности пути и принципа "deny wins".
* **Высокоуровневый фасад (`VaultGatekeeper`):** Удобный API для проверки прав доступа ("может ли пользователь прочесть файл?") и фильтрации списков файловых путей.

## Быстрый старт

### 1. Написание политики `policy.yaml`

```yaml
default_deny: true  # Если нет разрешающих правил - доступ закрыт

roles:
  admin: [alice]
  editor: [bob, charlie]
  viewer: [dave]

rules:
  # Админ может всё
  - pattern: "**/*"
    roles: [admin]
    permissions: [all]
    priority: 100

  # Редакторы могут читать и писать, но не удалять
  - pattern: "**/*"
    roles: [editor]
    permissions: [read, write]
    priority: 50

  # Явный запрет редакторам (deny-override) на папку secrets
  - pattern: "secrets/**"
    roles: [editor]
    permissions: [read, write]
    deny: true
    priority: 60
```

### 2. Использование `VaultGatekeeper` в коде

```python
from vault_acl.loader import load_policy
from vault_acl.engine import RuleResolver
from vault_acl.gatekeeper import VaultGatekeeper

# 1. Загружаем объект политики (AclPolicy)
policy = load_policy("path/to/policy.yaml")

# 2. Создаём движок и оборачиваем фасад
resolver = RuleResolver(policy)
gatekeeper = VaultGatekeeper(resolver)

# 3. Проверка прав (возвращает True/False)
if gatekeeper.can_read("bob", "projects/plan.md"):
    print("Bob может читать")

if not gatekeeper.can_write("dave", "projects/plan.md"):
    print("Dave не может редактировать (у него роль viewer, нет правил)")

# 4. Фильтрация путей - выдать только те файлы, на которые у пользователя есть доступ
all_files = ["docs/a.md", "secrets/pass.md", "daily/1.md"]
readable_by_bob = gatekeeper.filter_readable("bob", all_files)
# Вернёт: ["docs/a.md", "daily/1.md"]
```

## Inline ACL в заголовке файла (Frontmatter)

В дополнение к глобальной политике, права можно прописать прямо в YAML-заголовке каждого файла. Такие правила имеют повышенный приоритет (по умолчанию `200`) и автоматически привязываются к пути этого файла.

### Пример markdown-файла с inline ACL

```markdown
---
title: Секретный план проекта
acl:
  - users: [dave]
    permissions: [read, write]
  - roles: [editor]
    permissions: [delete]
    deny: true
  - roles: [admin]
    permissions: [all]
---
# Содержимое документа
...
```

Здесь:
- `dave` персонально получает `read` + `write` на этот файл (даже если глобально у него роль `viewer`).
- Роль `editor` **не может** удалять этот файл (`deny: true`).
- `admin` по-прежнему может всё.

### Использование в коде

```python
from vault_acl import extract_acl_from_markdown, RuleResolver

# 1. Прочитать markdown файл
with open("docs/plan.md") as f:
    text = f.read()

# 2. Извлечь inline-правила
inline_rules = extract_acl_from_markdown(text, "docs/plan.md")

# 3. Зарегистрировать их в движке
resolver.register_inline_rules("docs/plan.md", inline_rules)

# Теперь resolve_permissions / can / filter_accessible учитывают inline-правила
```

## Запрос доступа (Access Request System)

Пользователь может запросить доступ к файлу у его владельца — временно (на N минут) или навсегда.

### Жизненный цикл

```
Пользователь → create_request() → PENDING
                                      ↓
                    Владелец → approve() → APPROVED → AccessGrant (active)
                             → deny()    → DENIED
                             → revoke()  → REVOKED (отзыв ранее выданного)
                                                       ↓ (через TTL)
                                                    EXPIRED (автоматически)
```

### Пример использования

```python
from vault_acl import GrantStore, GrantType, Permission, RuleResolver

store = GrantStore()

# 1. Пользователь запрашивает доступ
req = store.create_request(
    requester="dave",
    file_path="secrets/plan.md",
    owner="alice",
    permissions=Permission.READ | Permission.WRITE,
    grant_type=GrantType.TEMPORARY,   # или GrantType.PERMANENT
    ttl_minutes=60,                   # доступ на 1 час
    reason="Нужно посмотреть для совещания",
)

# 2. Владелец видит список входящих запросов
pending = store.pending_for_owner("alice")

# 3. Владелец одобряет
grant = store.approve(req.id, approved_by="alice")
# grant.expires_at ≈ now + 60 min

# 4. Подключаем store к движку — гранты автоматически учитываются
resolver = RuleResolver(policy, grant_store=store)
resolver.can("dave", "secrets/plan.md", Permission.READ)  # True!

# 5. Владелец может отозвать доступ досрочно
store.revoke(grant.id, revoked_by="alice")
```

Приоритет грантов = **250** (выше inline-правил = 200, выше глобальных = 0–100).

## Структура пакета

* `models.py` — Датаклассы (AclPolicy, AccessRule, UserIdentity) и флаги прав (Permission).
* `engine.py` — `RuleResolver`, ядро системы. Вычисляет победившее правило для каждого отдельного бита прав (детали см. в [ALGO.md](ALGO.md)).
* `gatekeeper.py` — Высокоуровневый фасад (`can_read`, `can_write`, `filter_readable`).
* `loader.py` — YAML парсер, возвращающий объекты моделей.
* `frontmatter.py` — Парсер inline ACL из YAML-заголовков markdown-файлов.
* `grants.py` — Система запросов доступа (AccessRequest, AccessGrant, GrantStore).
* `interfaces/vault_acl.py` — Внешний ABC-интерфейс `BaseAccessResolver` для инверсии зависимостей.
