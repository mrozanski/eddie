from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from typing import List, Any, Optional, Dict
from pydantic import BaseModel, Field
from search_tools import playwright_tools
from langchain_tavily import TavilySearch
from langchain_community.agent_toolkits.openapi.toolkit import RequestsToolkit
from langchain_community.utilities.requests import TextRequestsWrapper
from langchain.retrievers.document_compressors import (
    LLMChainExtractor, 
    LLMChainFilter, 
    EmbeddingsFilter,
    DocumentCompressorPipeline
)
from langchain_community.document_transformers import EmbeddingsRedundantFilter
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document
import uuid
import asyncio
from datetime import datetime
from IPython.display import Image, display
from models.product_models import ProductSearchInput
import tiktoken

load_dotenv(override=True)

class State(TypedDict):
    messages: Annotated[List[Any], add_messages]

class EvaluatorOutput(BaseModel):
    feedback: str = Field(description="Feedback on the assistant's response")
    success_criteria_met: bool = Field(description="Whether the success criteria have been met")
    user_input_needed: bool = Field(description="True if more input is needed from the user, or clarifications, or the assistant is stuck")

class LangChainContextManager:
    """Uses LangChain's built-in contextual compression tools for better content management"""
    
    def __init__(self, max_tokens: int = 100000):
        self.max_tokens = max_tokens
        self.encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        
        # Initialize LangChain compression tools
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.embeddings = OpenAIEmbeddings()
        
        # Create document compressor pipeline
        self._setup_compressors()
    
    def _setup_compressors(self):
        """Setup LangChain compressors for different use cases"""
        
        # 1. LLM-based extractor for web content
        self.content_extractor = LLMChainExtractor.from_llm(
            self.llm
        )
        
        # 2. LLM-based filter for relevance
        self.relevance_filter = LLMChainFilter.from_llm(
            self.llm,
            top_n=3
        )
        
        # 3. Embeddings-based filter for similarity
        self.similarity_filter = EmbeddingsFilter(
            embeddings=self.embeddings,
            similarity_threshold=0.76
        )
        
        # 4. Redundant content filter
        self.redundant_filter = EmbeddingsRedundantFilter(
            embeddings=self.embeddings
        )
        
        # 5. Text splitter for large documents
        self.text_splitter = CharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separator=". "
        )
        
        # 6. Combined pipeline
        self.pipeline_compressor = DocumentCompressorPipeline(
            transformers=[
                self.text_splitter,
                self.redundant_filter,
                self.similarity_filter
            ]
        )
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))
    
    def compress_web_content(self, html_content: str, query: str = "guitar specifications") -> str:
        """Use LangChain extractor to compress web content"""
        if not html_content or len(html_content) < 1000:
            return html_content
        
        try:
            # Create a document from the HTML content
            doc = Document(page_content=html_content, metadata={"source": "web"})
            
            # Use LLM extractor to get relevant information
            compressed_docs = self.content_extractor.compress_documents([doc], query)
            
            if compressed_docs:
                return compressed_docs[0].page_content
            else:
                # Fallback to simple text extraction
                return self._simple_text_extraction(html_content)
                
        except Exception as e:
            print(f"Compression failed, using fallback: {e}")
            return self._simple_text_extraction(html_content)
    
    def _simple_text_extraction(self, html_content: str) -> str:
        """Simple fallback text extraction"""
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_content)
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Limit length
        return text[:3000] + "..." if len(text) > 3000 else text
    
    def filter_messages(self, messages: List[Any], system_message: str) -> List[Any]:
        """Filter messages using LangChain compressors"""
        if not messages:
            return messages
        
        # Count system message tokens
        system_tokens = self.count_tokens(system_message)
        available_tokens = self.max_tokens - system_tokens - 1000
        
        # Convert messages to documents for compression
        docs = []
        for msg in messages:
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                docs.append(Document(
                    page_content=msg.content,
                    metadata={"type": type(msg).__name__, "message": msg}
                ))
        
        if not docs:
            return messages
        
        try:
            # Use relevance filter to keep only relevant messages
            filtered_docs = self.relevance_filter.compress_documents(
                docs, 
                "guitar research and specifications"
            )
            
            # Convert back to messages
            filtered_messages = []
            for doc in filtered_docs:
                if "message" in doc.metadata:
                    filtered_messages.append(doc.metadata["message"])
            
            # Ensure we stay within token limits
            return self._truncate_to_token_limit(filtered_messages, available_tokens)
            
        except Exception as e:
            print(f"Message filtering failed, using fallback: {e}")
            return self._truncate_to_token_limit(messages, available_tokens)
    
    def _truncate_to_token_limit(self, messages: List[Any], available_tokens: int) -> List[Any]:
        """Truncate messages to stay within token limits"""
        truncated_messages = []
        current_tokens = 0
        
        for message in reversed(messages):
            message_content = message.content if hasattr(message, 'content') else str(message)
            message_tokens = self.count_tokens(message_content)
            
            if current_tokens + message_tokens <= available_tokens:
                truncated_messages.insert(0, message)
                current_tokens += message_tokens
            else:
                # Truncate this message if it's too large
                if message_tokens > available_tokens - current_tokens:
                    truncated_content = self._truncate_content(message_content, available_tokens - current_tokens)
                    if hasattr(message, '__class__'):
                        truncated_message = message.__class__(content=truncated_content)
                    else:
                        truncated_message = AIMessage(content=truncated_content)
                    truncated_messages.insert(0, truncated_message)
                break
        
        return truncated_messages
    
    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """Truncate content to fit within token limit"""
        tokens = self.encoding.encode(content)
        if len(tokens) <= max_tokens:
            return content
        
        truncated_tokens = tokens[:max_tokens-10]
        truncated_text = self.encoding.decode(truncated_tokens)
        return truncated_text + "... [truncated]"

class LangChainRequestsWrapper(TextRequestsWrapper):
    """Custom requests wrapper using LangChain compression"""
    
    def __init__(self, context_manager: LangChainContextManager, **kwargs):
        super().__init__(**kwargs)
        self.context_manager = context_manager
    
    def get(self, url: str, **kwargs) -> str:
        """Override get method to use LangChain compression"""
        try:
            content = super().get(url, **kwargs)
            if len(content) > 1000:  # Only compress large content
                return self.context_manager.compress_web_content(content)
            return content
        except Exception as e:
            return f"Error fetching content from {url}: {str(e)}"

class ProductSearchAgentV2:
    def __init__(self, input=None):
        self.worker_llm_with_tools = None
        self.evaluator_llm_with_output = None
        self.tools = None
        self.llm_with_tools = None
        self.graph = None
        self.job_search_id = str(uuid.uuid4())
        self.memory = MemorySaver()
        self.browser = None
        self.playwright = None
        self.context_manager = LangChainContextManager()
        self.max_tool_calls_per_iteration = 3
        self.search_success_criteria = ""
        self.input = input

    async def setup(self):
        # Initialize Tavily Search Tool with reduced results
        tavily_search_tool = TavilySearch(
            max_results=3,
            topic="general",
        )
        
        # Initialize Requests Toolkit with LangChain compression
        requests_toolkit = RequestsToolkit(
            requests_wrapper=LangChainRequestsWrapper(self.context_manager, headers={}),
            allow_dangerous_requests=True,
        )
        requests_tools = requests_toolkit.get_tools()
        
        # Get playwright tools
        playwright_tools_list, self.browser, self.playwright = await playwright_tools()
        
        # Combine all tools
        self.tools = [tavily_search_tool] + requests_tools + playwright_tools_list
        
        worker_llm = ChatOpenAI(model="gpt-4o-mini")
        self.worker_llm_with_tools = worker_llm.bind_tools(self.tools)
        evaluator_llm = ChatOpenAI(model="gpt-4o-mini")
        self.evaluator_llm_with_output = evaluator_llm.with_structured_output(EvaluatorOutput)
        await self.build_graph()

    def _load_system_prompt(self) -> str:
        """Load and format the system prompt"""
        try:
            with open("config/guitar_registry_prompt.md", "r", encoding="utf-8") as f:
                prompt_content = f.read()
            
            prompt_template = PromptTemplate.from_template(prompt_content)
            
            if self.input and hasattr(self.input, 'manufacturer') and hasattr(self.input, 'product_name') and hasattr(self.input, 'year'):
                formatted_prompt = prompt_template.invoke({
                    "manufacturer": self.input.manufacturer,
                    "model": self.input.product_name,
                    "year": self.input.year
                })
                return str(formatted_prompt)
            else:
                return prompt_content
                
        except FileNotFoundError:
            return "Error: Could not load system prompt from config/guitar_registry_prompt.md"
        except Exception as e:
            return f"Error loading system prompt: {str(e)}"

    def worker(self, state: State) -> Dict[str, Any]:
        # Load and format the system prompt
        system_message = self._load_system_prompt()
        
        # Get existing messages and filter them using LangChain
        existing_messages = state.get("messages", [])
        filtered_messages = self.context_manager.filter_messages(existing_messages, system_message)
        
        # Combine system message with filtered messages
        messages = [SystemMessage(content=system_message)]
        messages.extend(filtered_messages)
        
        print(f"=== WORKER INVOCATION (LangChain Version) ===")
        print(f"System prompt loaded: {len(system_message)} characters")
        print(f"Original messages: {len(existing_messages)}")
        print(f"Filtered messages: {len(filtered_messages)}")
        print(f"Total messages in state: {len(messages)}")
        
        # Estimate token usage
        total_content = system_message + " ".join([str(m.content) for m in messages if hasattr(m, 'content')])
        estimated_tokens = self.context_manager.count_tokens(total_content)
        print(f"Estimated tokens: {estimated_tokens:,}")
        
        # Check if we have a human message to respond to
        human_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
        if human_messages:
            print(f"Human message: {human_messages[-1].content[:100]}...")
        else:
            print("No human message found, adding a default research request")
            messages.append(HumanMessage(content="Please research this guitar model thoroughly using all available tools."))

        # Invoke the LLM with tools
        print("Invoking LLM with tools...")
        response = self.worker_llm_with_tools.invoke(messages)
        print(f"LLM response type: {type(response)}")
        print(f"LLM response content: {response.content[:200]}...")
        
        # Check for tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print(f"Tool calls made: {len(response.tool_calls)}")
            for tool_call in response.tool_calls:
                print(f"  - {tool_call['name']}: {tool_call['args']}")
        else:
            print("No tool calls in response")
        
        # Return updated state
        return {
            "messages": [response],
        }

    async def build_graph(self):
        # Custom tool node with debugging and tool call limiting
        def debug_tool_node(state: State):
            print("=== TOOL NODE INVOCATION ===")
            print(f"State messages: {len(state.get('messages', []))}")
            
            # Get the last message to check for tool calls
            last_message = state["messages"][-1] if state.get("messages") else None
            if last_message and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                # Limit tool calls to prevent context overflow
                tool_calls = last_message.tool_calls[:self.max_tool_calls_per_iteration]
                if len(last_message.tool_calls) > self.max_tool_calls_per_iteration:
                    print(f"⚠️  Limiting tool calls from {len(last_message.tool_calls)} to {self.max_tool_calls_per_iteration}")
                
                print(f"Executing {len(tool_calls)} tool calls...")
                for tool_call in tool_calls:
                    print(f"  Executing: {tool_call['name']}")
                
                # Create a modified message with limited tool calls
                modified_message = last_message.__class__(
                    content=last_message.content,
                    tool_calls=tool_calls
                )
                modified_state = {"messages": state["messages"][:-1] + [modified_message]}
            else:
                print("No tool calls to execute")
                modified_state = state
            
            # Use the standard ToolNode
            tool_node = ToolNode(tools=self.tools)
            result = tool_node.invoke(modified_state)
            print("Tool execution completed")
            return result
        
        # Set up Graph Builder with State
        graph_builder = StateGraph(State)

        # Add nodes
        graph_builder.add_node("tools", debug_tool_node)
        graph_builder.add_node("worker", self.worker)
        graph_builder.add_edge(START, "worker")
        graph_builder.add_conditional_edges("worker", tools_condition)
        graph_builder.add_edge("tools", "worker")

        # Compile the graph
        self.graph = graph_builder.compile(checkpointer=self.memory)

    async def run_superstep(self, message):
        config = {"configurable": {"thread_id": self.job_search_id}}

        state = {
            "messages": message
        }
        return await self.graph.ainvoke(state, config=config)
    
    def cleanup(self):
        if self.browser:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.browser.close())
                if self.playwright:
                    loop.create_task(self.playwright.stop())
            except RuntimeError:
                # If no loop is running, do a direct run
                asyncio.run(self.browser.close())
                if self.playwright:
                    asyncio.run(self.playwright.stop()) 