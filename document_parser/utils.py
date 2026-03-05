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
    def walk(blocks, prefix=""):
        # Словарь для хранения max номера на каждом уровне
        level_nums = {}
        for block in blocks:
            bid = str(block.get("id"))
            if not bid:
                continue
            parts = bid.split(".")
            # Сравниваем с ожидаемым номером на каждом уровне
            for i, num in enumerate(parts):
                lvl = i
                expected = level_nums.get(lvl, 0) + 1
                actual = int(num)
                if actual != expected:
                    return False
                level_nums[lvl] = actual

            # Рекурсивно проверяем вложенные list_items
            if block.get("type") == "list":
                for item in block.get("items", {}).get("items", []):
                    nested = item.get("lists", [])
                    if nested:
                        if not walk([{"type": "list", "items": n} for n in nested]):
                            return False

            # Проверяем children у blockquote
            if block.get("type") == "blockquote":
                if not walk(block.get("children", [])):
                    return False
        return True

    return walk(document)


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
