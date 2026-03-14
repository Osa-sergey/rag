from pathlib import Path
from typing import Dict, List
import yaml


# ───────────────────────────────────────
# ЗАГРУЗКА YAML
# ───────────────────────────────────────

def load_yaml(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ───────────────────────────────────────
# FLATTЕН БЛОКОВ
# ───────────────────────────────────────

def flatten_blocks(blocks: List[Dict]) -> List[Dict]:
    """
    Превращает document в линейный список всех блоков с id.
    """
    flat = []

    def walk(block):
        if "id" in block:
            flat.append(block)

        btype = block.get("type")

        if btype == "list":
            for item in block.get("items", {}).get("items", []):
                flat.append({
                    "id": str(item["id"]),
                    "type": "list_item",
                    "paragraphs": item.get("paragraphs", []),
                    "lists": item.get("lists", [])
                })
                for nested in item.get("lists", []):
                    walk({"type": "list", "id": nested.get("id"), "items": nested})

        elif btype == "blockquote":
            for child in block.get("children", []):
                walk(child)

    for b in blocks:
        walk(b)

    return flat


# ───────────────────────────────────────
# ПЕЧАТЬ ВСЕХ ID
# ───────────────────────────────────────

def list_all_ids(document: List[Dict]) -> List[str]:
    """
    Возвращает список всех id из документа.
    """
    return [str(b["id"]) for b in flatten_blocks(document) if "id" in b]


def print_available_ids(yaml_path: Path):
    """
    Печатает все id из YAML документа.
    """
    data = load_yaml(yaml_path)
    for bid in list_all_ids(data["document"]):
        print(bid)


# ───────────────────────────────────────
# ПРОВЕРКА ПОСЛЕДОВАТЕЛЬНОСТИ
# ───────────────────────────────────────

def check_id_sequence(document: List[Dict]) -> bool:
    """
    Проверяет, что номера на каждом уровне идут по порядку без пробелов.
    Возвращает True, если последовательность корректна, иначе False.
    """
    flat = flatten_blocks(document)

    # Для каждого родительского префикса отслеживаем последний номер ребёнка.
    # Пример: для ID "3.2.1" родитель = "3.2", номер ребёнка = 1.
    #         для ID "3"     родитель = "",    номер ребёнка = 3.
    parent_counters: Dict[str, int] = {}

    for block in flat:
        bid = str(block.get("id", ""))
        if not bid:
            continue

        parts = bid.split(".")
        # Пропускаем id с нечисловыми частями (например "None")
        if not parts[-1].isdigit():
            continue
        parent_prefix = ".".join(parts[:-1])  # "" для top-level
        child_num = int(parts[-1])

        last_seen = parent_counters.get(parent_prefix, 0)

        if child_num != last_seen + 1:
            # Допускаем повторное появление уже виденного номера
            # (тот же родитель, тот же ребёнок — дубликат в flat-представлении)
            if child_num <= last_seen:
                continue
            return False

        parent_counters[parent_prefix] = child_num

    return True


# ───────────────────────────────────────
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# ───────────────────────────────────────

if __name__ == "__main__":
    path = Path("parsed_yaml/983322_20260204_074140.yaml")

    print("=== ВСЕ ID ===")
    print_available_ids(path)

    data = load_yaml(path)
    is_correct = check_id_sequence(data["document"])
    print("\nПроверка последовательности ID:", "OK" if is_correct else "НАРУШЕНИЕ")
