import asyncio
import os

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

from rag_tools.langgraph_tools import get_tools

async def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("Skipping smoke test: OPENAI_API_KEY not set.")
        return
        
    print("Initializing LangGraph ReAct agent with 9 RAG tools...")
    
    # Enable LangChain tracing for better logs
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "rag_tools_smoke"
    
    # 1. Initialize LLM
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    # 2. Get tools from rag_tools package
    tools = get_tools()
    print(f"Loaded {len(tools)} tools: {[t.name for t in tools]}")
    
    # 3. Create prebuilt ReAct agent
    agent_executor = create_react_agent(llm, tools)
    
    # 4. Invoke agent
    query = "Какие статьи и концепты про RAG есть в системе?"
    print(f"\nUser: {query}")
    print("-" * 50)
    
    events = agent_executor.astream(
        {"messages": [HumanMessage(content=query)]},
        stream_mode="values"
    )
    
    async for event in events:
        last_msg = event["messages"][-1]
        print(f"[{last_msg.type}] {last_msg.content[:200]}...")

if __name__ == "__main__":
    asyncio.run(main())
