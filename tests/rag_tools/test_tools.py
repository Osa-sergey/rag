import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from rag_tools.schemas import (
    RaptorProcessInput, RaptorProcessOutput,
    RagSearchInput, RagSearchOutput,
    ListArticlesInput, ListArticlesOutput
)
from rag_tools.bootstrap import ToolContext
from rag_tools import tools
from rag_tools.langgraph_tools import get_tools
from rag_tools.mcp_server import mcp


def test_schema_validation():
    """Test that input schemas reject unknown fields and validate types."""
    # file_path is required
    with pytest.raises(ValueError):
        RaptorProcessInput()

    # Extra fields are forbidden in Inputs
    with pytest.raises(ValueError):
        RaptorProcessInput(file_path="test.md", extra_field="bad")

    # Valid input
    inp = RaptorProcessInput(file_path="test.yaml")
    assert inp.file_path == "test.yaml"
    assert inp.config_overrides == {}


@pytest.mark.asyncio
async def test_tool_functions(mocker):
    """Test core async tool functions with a mocked ToolContext."""
    mock_ctx = MagicMock(spec=ToolContext)
    
    # Mock raptor_pipeline behavior
    mock_pipeline = MagicMock()
    mock_pipeline.process_file.return_value = {
        "article_id": "test_123",
        "chunks": 5,
        "raptor_nodes": 10
    }
    mock_ctx.build_raptor_pipeline.return_value = mock_pipeline
    
    # Mock auto-convert to yaml to just return the passed string
    mocker.patch("rag_tools.tools._ensure_yaml", return_value="test.yaml")

    inp = RaptorProcessInput(file_path="test.md")
    out = await tools.raptor_process(inp, mock_ctx)
    
    # Check outputs mapped correctly
    assert isinstance(out, RaptorProcessOutput)
    assert out.article_id == "test_123"
    assert out.chunks == 5
    
    # Ensure pipeline was called
    mock_pipeline.process_file.assert_called_once_with("test.yaml")


def test_langgraph_tools():
    """Test LangGraph wrappers."""
    tools_list = get_tools()
    assert len(tools_list) == 9
    
    names = {t.name for t in tools_list}
    expected = {
        "raptor_process", "concept_build", "concept_expand", 
        "concept_dry_run", "rag_search", "concept_inspect",
        "list_articles", "list_concepts", "parse_document"
    }
    assert names == expected
    
    # Check that schema matches
    raptor_tool = next(t for t in tools_list if t.name == "raptor_process")
    schema = raptor_tool.args_schema.model_json_schema()
    assert "file_path" in schema["properties"]


@pytest.mark.asyncio
async def test_mcp_server():
    """Test MCP server tools list."""
    mcp_tools = await mcp.list_tools()
    assert len(mcp_tools) == 9
    
    names = {t.name for t in mcp_tools}
    expected = {
        "raptor_process", "concept_build", "concept_expand", 
        "concept_dry_run", "rag_search", "concept_inspect",
        "list_articles", "list_concepts", "parse_document"
    }
    assert names == expected
