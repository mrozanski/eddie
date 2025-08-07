from playwright.async_api import async_playwright
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.utilities.requests import TextRequestsWrapper
from langchain_core.tools import BaseTool
from typing import Any, Dict, List
import re

# load_dotenv(override=True)
# pushover_token = os.getenv("PUSHOVER_TOKEN")
# pushover_user = os.getenv("PUSHOVER_USER")
# pushover_url = "https://api.pushover.net/1/messages.json"
# serper = GoogleSerperAPIWrapper()

class SummarizingRequestsWrapper(TextRequestsWrapper):
    """Custom requests wrapper that summarizes web content to reduce token usage"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._max_content_length = 3000  # Maximum content length to return
    
    @property
    def max_content_length(self):
        return self._max_content_length
    
    def _extract_key_info(self, html_content: str) -> str:
        """Extract key information from HTML content"""
        if not html_content:
            return ""
        
        # Remove HTML tags and excessive whitespace
        text = re.sub(r'<[^>]+>', ' ', html_content)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Extract key information patterns (guitar specs, prices, etc.)
        key_patterns = [
            r'\b\d{4}\b',  # Years
            r'\$\d+(?:,\d{3})*(?:\.\d{2})?',  # Prices
            r'\b(?:mahogany|maple|rosewood|ebony|alder|ash|basswood)\b',  # Woods
            r'\b(?:HH|SSS|HSS|HS|SS|H)\b',  # Pickup configurations
            r'\b\d+(?:\.\d+)?\s*(?:inch|in|")\b',  # Measurements
            r'\b(?:Fender|Gibson|PRS|Ibanez|ESP|Jackson|Schecter)\b',  # Manufacturers
            r'\b(?:Mustang|Stratocaster|Telecaster|Les Paul|SG|Explorer)\b',  # Model names
        ]
        
        extracted_info = []
        for pattern in key_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                extracted_info.extend(matches[:3])  # Limit matches per pattern
        
        # Combine extracted info with truncated content
        summary = f"Key info: {', '.join(set(extracted_info))}\n\n"
        summary += f"Content preview: {text[:self.max_content_length]}..."
        
        return summary
    
    def get(self, url: str, **kwargs) -> str:
        """Override get method to summarize content"""
        try:
            content = super().get(url, **kwargs)
            if len(content) > self.max_content_length:
                return self._extract_key_info(content)
            return content
        except Exception as e:
            return f"Error fetching content from {url}: {str(e)}"

async def playwright_tools():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=browser)
    return toolkit.get_tools(), browser, playwright

def get_summarizing_requests_tools():
    """Get requests tools with content summarization"""
    from langchain_community.agent_toolkits.openapi.toolkit import RequestsToolkit
    
    # Use our custom wrapper
    requests_wrapper = SummarizingRequestsWrapper(headers={})
    toolkit = RequestsToolkit(
        requests_wrapper=requests_wrapper,
        allow_dangerous_requests=True,
    )
    return toolkit.get_tools()


# def push(text: str):
#     """Send a push notification to the user"""
#     requests.post(pushover_url, data = {"token": pushover_token, "user": pushover_user, "message": text})
#     return "success"


# def get_file_tools():
#     toolkit = FileManagementToolkit(root_dir="sandbox")
#     return toolkit.get_tools()


# async def other_tools():
#     push_tool = Tool(name="send_push_notification", func=push, description="Use this tool when you want to send a push notification")
#     file_tools = get_file_tools()

#     tool_search =Tool(
#         name="search",
#         func=serper.run,
#         description="Use this tool when you want to get the results of an online web search"
#     )

#     wikipedia = WikipediaAPIWrapper()
#     wiki_tool = WikipediaQueryRun(api_wrapper=wikipedia)

#     python_repl = PythonREPLTool()
    
#     return file_tools + [push_tool, tool_search, python_repl,  wiki_tool]

