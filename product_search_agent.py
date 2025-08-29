from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from typing import List, Any, Optional, Dict
from pydantic import BaseModel, Field
from search_tools import playwright_tools
from langchain_tavily import TavilySearch
from langchain_community.agent_toolkits.openapi.toolkit import RequestsToolkit
from langchain_community.utilities.requests import TextRequestsWrapper
import uuid
import asyncio
from datetime import datetime
from IPython.display import Image, display
from models.product_models import ProductSearchInput, GuitarRegistryOutput
import tiktoken
import re

load_dotenv(override=True)

class State(TypedDict):
    messages: Annotated[List[Any], add_messages]

class EvaluatorOutput(BaseModel):
    feedback: str = Field(description="Feedback on the assistant's response")
    success_criteria_met: bool = Field(description="Whether the success criteria have been met")
    user_input_needed: bool = Field(description="True if more input is needed from the user, or clarifications, or the assistant is stuck")

class ContentSummarizer(BaseModel):
    """Helper class to summarize web content to reduce token usage"""
    
    @staticmethod
    def extract_key_info(html_content: str, max_length: int = 2000) -> str:
        """Extract key information from HTML content and truncate to reduce tokens"""
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
        ]
        
        extracted_info = []
        for pattern in key_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                extracted_info.extend(matches[:5])  # Limit matches per pattern
        
        # Combine extracted info with truncated content
        summary = f"Key info: {', '.join(set(extracted_info))}\n\n"
        summary += f"Content preview: {text[:max_length]}..."
        
        return summary

class ContextManager:
    """Manages conversation context to prevent token limit issues"""
    
    def __init__(self, max_tokens: int = 100000):
        self.max_tokens = max_tokens
        self.encoding = tiktoken.encoding_for_model("gpt-4o-mini")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))
    
    def truncate_messages(self, messages: List[Any], system_message: str) -> List[Any]:
        """Truncate messages to stay within token limits"""
        if not messages:
            return messages
        
        # Count system message tokens
        system_tokens = self.count_tokens(system_message)
        available_tokens = self.max_tokens - system_tokens - 1000  # Buffer for safety
        
        # Start with most recent messages and work backwards
        truncated_messages = []
        current_tokens = 0
        
        for message in reversed(messages):
            message_content = message.content if hasattr(message, 'content') else str(message)
            message_tokens = self.count_tokens(message_content)
            
            if current_tokens + message_tokens <= available_tokens:
                truncated_messages.insert(0, message)
                current_tokens += message_tokens
            else:
                # If this message is too large, truncate it
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
        
        # Truncate and add ellipsis
        truncated_tokens = tokens[:max_tokens-10]  # Leave room for ellipsis
        truncated_text = self.encoding.decode(truncated_tokens)
        return truncated_text + "... [truncated]"

class ProductSearchAgent:
    def __init__(self, input=None, enable_db: bool = True, structured_output: bool = False):
        self.worker_llm_with_tools = None
        self.worker_llm_structured = None
        self.evaluator_llm_with_output = None
        self.tools = None
        self.llm_with_tools = None
        self.graph = None
        self.job_search_id = str(uuid.uuid4())
        self.memory = MemorySaver()
        self.browser = None
        self.playwright = None
        self.context_manager = ContextManager()
        self.content_summarizer = ContentSummarizer()
        self.max_tool_calls_per_iteration = 3  # Limit tool calls per iteration
        # To-do: save criteria to file and load here
        self.search_success_criteria = ""
        
        # Store user preferences
        self.input = input
        
        # Database integration settings
        self.enable_db = enable_db
        self.db_connection = None
        
        # Structured output settings
        self.structured_output = structured_output

    async def setup(self):
        # Initialize Tavily Search Tool with reduced results
        tavily_search_tool = TavilySearch(
            max_results=3,  # Reduced from 5 to 3
            topic="general",
        )
        
        # Initialize Requests Toolkit with content processing
        from search_tools import get_summarizing_requests_tools
        requests_tools = get_summarizing_requests_tools()
        
        # Get playwright tools
        playwright_tools_list, self.browser, self.playwright = await playwright_tools()
        
        # Combine all tools
        self.tools = [tavily_search_tool] + requests_tools + playwright_tools_list
        
        # Add database tools if enabled
        if self.enable_db:
            try:
                from db_tools import initialize_database, manufacturer_lookup_tool
                self.db_connection = await initialize_database()
                if self.db_connection:
                    db_tools = [manufacturer_lookup_tool]
                    self.tools.extend(db_tools)
                    print(f"Database integration enabled with {len(db_tools)} tool")
                else:
                    print("Database integration failed to initialize, continuing without DB tools")
            except Exception as e:
                print(f"Failed to setup database tools: {e}. Continuing without database integration.")
        
        worker_llm = ChatOpenAI(model="gpt-4o-mini")
        self.worker_llm_with_tools = worker_llm.bind_tools(self.tools)
        
        # Create structured output version for JSON generation
        if self.structured_output:
            self.worker_llm_structured = worker_llm.with_structured_output(GuitarRegistryOutput)
        
        evaluator_llm = ChatOpenAI(model="gpt-4o-mini")
        self.evaluator_llm_with_output = evaluator_llm.with_structured_output(EvaluatorOutput)
        await self.build_graph()

    def _load_system_prompt(self) -> str:
        """
        Load the system prompt from the config file and format it with input values using LangChain PromptTemplate.
        
        Returns:
            Formatted system prompt string
        """
        try:
            with open("config/guitar_registry_prompt.md", "r", encoding="utf-8") as f:
                prompt_content = f.read()
            
            # Create LangChain PromptTemplate
            prompt_template = PromptTemplate.from_template(prompt_content)
            
            # Extract values from self.input (ProductSearchInput object)
            if self.input and hasattr(self.input, 'manufacturer') and hasattr(self.input, 'product_name') and hasattr(self.input, 'year'):
                formatted_prompt = prompt_template.invoke({
                    "manufacturer": self.input.manufacturer,
                    "model": self.input.product_name,  # Note: prompt uses 'model' but input has 'product_name'
                    "year": self.input.year
                })
                return str(formatted_prompt)
            else:
                # Return unformatted template if no input provided
                return prompt_content
                
        except FileNotFoundError:
            return "Error: Could not load system prompt from config/guitar_registry_prompt.md"
        except Exception as e:
            return f"Error loading system prompt: {str(e)}"

    def _process_tool_results(self, messages: List[Any]) -> List[Any]:
        """Process and summarize tool results to reduce token usage"""
        processed_messages = []
        
        for message in messages:
            if hasattr(message, 'content') and isinstance(message.content, str):
                # Check if this looks like web content (contains HTML or is very long)
                if len(message.content) > 5000 or '<' in message.content:
                    # Summarize web content
                    summarized_content = self.content_summarizer.extract_key_info(message.content)
                    
                    # Create a new message safely by copying all attributes and updating content
                    try:
                        # Get all the message attributes
                        message_dict = message.model_dump() if hasattr(message, 'model_dump') else {}
                        
                        # Update the content
                        message_dict['content'] = summarized_content
                        
                        # Create new message with all original attributes
                        if hasattr(message, '__class__'):
                            processed_message = message.__class__(**message_dict)
                        else:
                            # Fallback to AIMessage if we can't determine the class
                            processed_message = AIMessage(content=summarized_content)
                            
                    except Exception as e:
                        print(f"Warning: Could not recreate message, using fallback: {e}")
                        # Fallback: create a simple message with just the content
                        processed_message = AIMessage(content=summarized_content)
                    
                    processed_messages.append(processed_message)
                else:
                    processed_messages.append(message)
            else:
                processed_messages.append(message)
        
        return processed_messages

    def worker(self, state: State) -> Dict[str, Any]:
        # Load and format the system prompt
        system_message = self._load_system_prompt()
        
        # Get existing messages and process them
        existing_messages = state.get("messages", [])
        processed_messages = self._process_tool_results(existing_messages)
        
        # Truncate messages to stay within token limits
        truncated_messages = self.context_manager.truncate_messages(processed_messages, system_message)
        
        # Combine system message with truncated messages
        messages = [SystemMessage(content=system_message)]
        messages.extend(truncated_messages)
        
        print(f"=== WORKER INVOCATION ===")
        print(f"System prompt loaded: {len(system_message)} characters")
        print(f"Original messages: {len(existing_messages)}")
        print(f"Processed messages: {len(processed_messages)}")
        print(f"Truncated messages: {len(truncated_messages)}")
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
        # Node
        def tool_calling_llm(state: State):
            return {"messages": [self.worker_llm_with_tools.invoke(state["messages"])]}
        
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
                
                # Create a modified message with limited tool calls safely
                try:
                    # Get all the message attributes
                    message_dict = last_message.model_dump() if hasattr(last_message, 'model_dump') else {}
                    
                    # Update the tool calls
                    message_dict['tool_calls'] = tool_calls
                    
                    # Create new message with all original attributes
                    if hasattr(last_message, '__class__'):
                        modified_message = last_message.__class__(**message_dict)
                    else:
                        # Fallback to AIMessage if we can't determine the class
                        modified_message = AIMessage(content=last_message.content, tool_calls=tool_calls)
                        
                except Exception as e:
                    print(f"Warning: Could not recreate message, using fallback: {e}")
                    # Fallback: create a simple message with just the content and tool calls
                    modified_message = AIMessage(content=last_message.content, tool_calls=tool_calls)
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
        # graph_builder.add_node("evaluator", self.search_evaluator)

        # Add edges
        # graph_builder.add_conditional_edges("worker", self.worker_router, {"tools": "worker", "evaluator": "evaluator"})
        # graph_builder.add_edge("tools", "worker")
        # graph_builder.add_conditional_edges("evaluator", self.route_based_on_evaluation, {"worker": "worker", "END": END})
        # graph_builder.add_edge(START, "worker")

        # Compile the graph
        self.graph = graph_builder.compile(checkpointer=self.memory)
        # display(Image(self.graph.get_graph(xray=True).draw_mermaid_png()))

    async def run_superstep(self, message):
        config = {"configurable": {"thread_id": self.job_search_id}}

        state = {
            "messages": message
        }
        return await self.graph.ainvoke(state, config=config)
    
    async def generate_structured_output(self) -> GuitarRegistryOutput:
        """
        Generate structured JSON output based on the research data collected.
        This should be called after running the research workflow.
        """
        if not self.structured_output or not self.worker_llm_structured:
            raise ValueError("Structured output not enabled. Initialize with structured_output=True")
        
        config = {"configurable": {"thread_id": self.job_search_id}}
        
        # Get the conversation history from memory
        state = await self.graph.aget_state(config)
        messages = state.values.get("messages", [])
        
        # Load and format the system prompt for JSON generation
        system_message = self._load_system_prompt()
        
        # Create a specific prompt for JSON generation
        json_prompt = """
Based on all the research data collected above, generate a complete JSON output for the guitar registry system.

IMPORTANT INSTRUCTIONS:
1. Extract all relevant information about the manufacturer, model, and individual guitar details
2. Use the complete model reference (Option A) if you have manufacturer name, model name, and year
3. If missing some model details, use fallback options appropriately
4. Include source attribution for where the information was found
5. Fill in as many fields as possible with accurate information from your research
6. Use "Research Analysis" as the source name
7. Set today's date for date_accessed if including URLs

Generate the structured JSON output now:
"""
        
        # Combine system message, research history, and JSON generation prompt
        full_messages = [SystemMessage(content=system_message)]
        full_messages.extend(messages)
        full_messages.append(HumanMessage(content=json_prompt))
        
        # Generate structured output
        result = await self.worker_llm_structured.ainvoke(full_messages)
        return result
    
    async def cleanup(self):
        """Clean up all resources properly"""
        # Clean up browser resources
        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                print(f"Warning: Error closing browser: {e}")
        
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                print(f"Warning: Error stopping playwright: {e}")
        
        # Clean up database resources
        if self.db_connection:
            try:
                await self._cleanup_database()
            except Exception as e:
                print(f"Warning: Error cleaning up database: {e}")
        
        # Clear references
        self.browser = None
        self.playwright = None
        self.db_connection = None
    
    async def _cleanup_database(self):
        """Helper method to clean up database connections"""
        if self.db_connection:
            try:
                from db_tools import cleanup_database
                await cleanup_database()
                self.db_connection = None
                print("Database connections cleaned up")
            except Exception as e:
                print(f"Error cleaning up database: {e}")
