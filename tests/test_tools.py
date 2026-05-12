import json

import pytest
from percival_agentmail_mcp.client import AgentMailClientWrapper
from percival_agentmail_mcp.config import ServerConfig

# --- Fixtures ---

@pytest.fixture
def mock_config():
    return ServerConfig(
        api_key="am_test_key_supersecret123",
        inbox_id="test@agentmail.to"
    )

@pytest.fixture
def wrapper(mock_config):
    return AgentMailClientWrapper(api_key=mock_config.api_key)


# --- Config Tests ---

def test_config_initialization(mock_config):
    assert mock_config.api_key == "am_test_key_supersecret123"
    assert mock_config.inbox_id == "test@agentmail.to"
    assert mock_config.max_results == 25
    assert mock_config.timeout == 30


# LOW-01: Verify API key is masked in repr/str
def test_config_repr_masks_api_key(mock_config):
    """LOW-01: __repr__ must NEVER contain the API key."""
    repr_str = repr(mock_config)
    assert "am_test_key_supersecret123" not in repr_str
    assert "****" in repr_str
    assert "test@agentmail.to" in repr_str


def test_config_str_masks_api_key(mock_config):
    """LOW-01: __str__ must NEVER contain the API key."""
    str_str = str(mock_config)
    assert "am_test_key_supersecret123" not in str_str
    assert "****" in str_str


# --- Client Wrapper Tests ---

# MED-03: Verify serialization without hasattr fallback
def test_wrapper_serialization_dict(wrapper):
    """Basic dict serialization."""
    test_dict = {"id": "123", "name": "Test"}
    serialized = wrapper._serialize(test_dict)
    assert serialized == test_dict


def test_wrapper_serialization_list(wrapper):
    """List serialization."""
    test_list = [{"a": 1}, {"b": 2}]
    serialized = wrapper._serialize(test_list)
    assert serialized == test_list


def test_wrapper_serialization_primitive(wrapper):
    """Primitive types should pass through unchanged."""
    assert wrapper._serialize("hello") == "hello"
    assert wrapper._serialize(42) == 42
    assert wrapper._serialize(None) is None


def test_wrapper_format_response_json(wrapper):
    """format_response should produce valid JSON."""
    data = {"id": "msg_123", "subject": "Test"}
    result = wrapper.format_response(data)
    parsed = json.loads(result)
    assert parsed["id"] == "msg_123"


# HIGH-02: Verify error sanitization
def test_format_error_generic_exception(wrapper):
    """HIGH-02: Generic exceptions must NOT leak internal details."""
    error = RuntimeError("/home/bill-kopp/.secret/api_key was not found")
    result = wrapper.format_error(error)
    parsed = json.loads(result)
    
    assert parsed["status"] == "error"
    # Must NOT contain the original error message with filesystem paths
    assert "/home/bill-kopp" not in parsed["message"]
    assert "internal error" in parsed["message"].lower()


# --- Security Constants Tests ---

def test_fencing_constants_exist():
    """HIGH-01: Fencing constants must be defined and non-empty."""
    from percival_agentmail_mcp.tools import CONTENT_FENCE_START, CONTENT_FENCE_END
    assert len(CONTENT_FENCE_START) > 10
    assert len(CONTENT_FENCE_END) > 10
    assert "NOT instructions" in CONTENT_FENCE_START


def test_max_results_cap():
    """MED-02: MAX_RESULTS_CAP must exist and be reasonable."""
    from percival_agentmail_mcp.tools import MAX_RESULTS_CAP
    assert MAX_RESULTS_CAP == 50
    assert MAX_RESULTS_CAP > 0
