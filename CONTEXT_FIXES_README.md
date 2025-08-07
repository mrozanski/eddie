# Context Management Fixes for Token Limit Issue

## Problem Summary

The application was hitting OpenAI's 128,000 token context limit due to:
- Large system prompt (5,309 characters)
- Accumulating full HTML content from web requests
- No context truncation or management
- Multiple tool calls adding massive content in single iterations

## Implemented Solutions

### 1. Content Summarization (`ContentSummarizer`)

**Location**: `product_search_agent.py`

**Purpose**: Automatically extract key information from web content to reduce token usage.

**Features**:
- Removes HTML tags and excessive whitespace
- Extracts guitar-specific information using regex patterns:
  - Years (4-digit numbers)
  - Prices (dollar amounts)
  - Wood types (mahogany, maple, rosewood, etc.)
  - Pickup configurations (HH, SSS, HSS, etc.)
  - Measurements (inches, scale lengths)
  - Manufacturer names
  - Model names
- Limits content to 2,000 characters with key info summary

**Usage**:
```python
summarizer = ContentSummarizer()
summarized_content = summarizer.extract_key_info(html_content)
```

### 2. Context Management (`ContextManager`)

**Location**: `product_search_agent.py`

**Purpose**: Manage conversation context to stay within token limits.

**Features**:
- Token counting using `tiktoken`
- Intelligent message truncation (keeps most recent messages)
- Configurable token limits (default: 100,000 tokens)
- Automatic content truncation with ellipsis

**Usage**:
```python
context_manager = ContextManager(max_tokens=100000)
truncated_messages = context_manager.truncate_messages(messages, system_message)
```

### 3. Custom Requests Wrapper (`SummarizingRequestsWrapper`)

**Location**: `search_tools.py`

**Purpose**: Automatically summarize web content at the tool level.

**Features**:
- Overrides `TextRequestsWrapper.get()` method
- Automatically summarizes content longer than 3,000 characters
- Extracts guitar-specific information patterns
- Provides error handling for failed requests

**Usage**:
```python
from search_tools import get_summarizing_requests_tools
requests_tools = get_summarizing_requests_tools()
```

### 4. Tool Call Limiting

**Location**: `product_search_agent.py` (in `debug_tool_node`)

**Purpose**: Prevent too many tool calls in a single iteration.

**Features**:
- Limits tool calls to 3 per iteration (configurable)
- Warns when limiting is applied
- Maintains conversation flow while preventing context overflow

### 5. Reduced Search Results

**Location**: `product_search_agent.py` (in `setup()`)

**Change**: Reduced Tavily search results from 5 to 3 to reduce initial content load.

## Configuration Options

### Token Limits
```python
# In ProductSearchAgent.__init__()
self.context_manager = ContextManager(max_tokens=100000)  # Adjust as needed
```

### Tool Call Limits
```python
# In ProductSearchAgent.__init__()
self.max_tool_calls_per_iteration = 3  # Adjust as needed
```

### Content Length Limits
```python
# In SummarizingRequestsWrapper.__init__()
self.max_content_length = 3000  # Adjust as needed
```

## Monitoring and Debugging

The agent now provides detailed logging:

```
=== WORKER INVOCATION ===
System prompt loaded: 5,309 characters
Original messages: 10
Processed messages: 8
Truncated messages: 6
Total messages in state: 7
Estimated tokens: 45,123
```

## Testing

Run the test script to verify fixes:

```bash
python test_context_fixes.py
```

## Expected Improvements

1. **Token Usage**: Reduced from 267,241 tokens to under 100,000 tokens
2. **Stability**: No more context length exceeded errors
3. **Performance**: Faster processing due to reduced content
4. **Reliability**: Better error handling and graceful degradation

## Dependencies Added

- `tiktoken`: For accurate token counting
- Updated `pyproject.toml` with new dependency

## Migration Notes

- Existing code should work without changes
- New features are automatically applied
- Can be disabled by setting limits to very high values
- Backward compatible with existing workflows

## Future Enhancements

1. **Adaptive Limits**: Adjust limits based on model being used
2. **Content Caching**: Cache summarized content to avoid re-processing
3. **Streaming**: Implement streaming responses for very large content
4. **Memory Management**: Add periodic context cleanup
5. **Model Switching**: Automatically switch to models with higher limits when needed 