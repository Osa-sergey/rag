"""Document parser package — markdown/HTML to structured YAML."""
from document_parser.structurizer import (
    html_to_ast,
    md_to_ast,
    process_md_file,
    process_csv,
    ArticleParser,
)
from document_parser.text_extractor import (
    render_block,
    flatten_blocks,
    extract_text_range,
    extract_from_yaml,
    list_all_ids,
    load_yaml,
)
from document_parser.links_extractor import collect_assets, process_yaml_file
from document_parser.utils import (
    check_id_sequence,
    print_available_ids as print_ids,
)
