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
from models.product_models import ProductSearchInput

load_dotenv(override=True)

class State(TypedDict):
    messages: Annotated[List[Any], add_messages]

class EvaluatorOutput(BaseModel):
    feedback: str = Field(description="Feedback on the assistant's response")
    success_criteria_met: bool = Field(description="Whether the success criteria have been met")
    user_input_needed: bool = Field(description="True if more input is needed from the user, or clarifications, or the assistant is stuck")


class ProductSearchAgent:
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
        # To-do: save criteria to file and load here
        self.search_success_criteria = ""
        
        # Store user preferences
        self.input = input

    async def setup(self):
        # Initialize Tavily Search Tool
        tavily_search_tool = TavilySearch(
            max_results=5,
            topic="general",
        )
        
        # Initialize Requests Toolkit
        requests_toolkit = RequestsToolkit(
            requests_wrapper=TextRequestsWrapper(headers={}),
            allow_dangerous_requests=True,  # ⚠️ Security note: Use with caution
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

    def worker(self, state: State) -> Dict[str, Any]:
        # Load and format the system prompt
        system_message = self._load_system_prompt()
        
        # Combine system message with existing messages from state
        messages = [SystemMessage(content=system_message)]
        if state.get("messages"):
            messages.extend(state["messages"])
        
        print(f"=== WORKER INVOCATION ===")
        print(f"System prompt loaded: {len(system_message)} characters")
        print(f"Total messages in state: {len(messages)}")
        
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
        
        # Custom tool node with debugging
        def debug_tool_node(state: State):
            print("=== TOOL NODE INVOCATION ===")
            print(f"State messages: {len(state.get('messages', []))}")
            
            # Get the last message to check for tool calls
            last_message = state["messages"][-1] if state.get("messages") else None
            if last_message and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                print(f"Executing {len(last_message.tool_calls)} tool calls...")
                for tool_call in last_message.tool_calls:
                    print(f"  Executing: {tool_call['name']}")
            else:
                print("No tool calls to execute")
            
            # Use the standard ToolNode
            tool_node = ToolNode(tools=self.tools)
            result = tool_node.invoke(state)
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
