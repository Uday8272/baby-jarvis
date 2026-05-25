
import os 
from dotenv import load_dotenv 
from typing import TypedDict, Annotated , List , Dict 
from langgraph.graph.message import add_messages 
from langgraph.graph import StateGraph, END 
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage 
from tavily import TavilyClient 
from langgraph.checkpoint.memory import MemorySaver 

# load the api keys from .env file securely 
load_dotenv() 

# initialize the brain 
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# defining the state ======================================================================
class agent_state(TypedDict): 
    # the list of messages act as out rolling short-term memory 
    messages: Annotated[list, add_messages] 
    
    # we store the user's query for easy reference 
    user_query: str 
    
    # we will store the unstructured data gathered by the researcher here 
    research_data: List[Dict[str, str]] 
    
    # The Verifier will update this flag so the Writer knows it is safe to proceed 
    is_verified: bool 
    
    search_count: int 
    
    # The final structured output to present to the user 
    final_output : str 
    
    
# defining the nodes ======================================================================
# agent1 --> intake agent ========================================================================
def intake_agent(state: agent_state): 
    ''' understands the query and plans the research ''' 
    print('intake agent: analyze user query ...') 
    
    # give the agent a strict persona and instructions 
    system_prompt = SystemMessage(
        content="You are a research planner. Read the user's query and write a brief, "
                "2-step plan on exactly what needs to be searched on the web to answer it. "
                "Keep it concise."
    ) 
    
    # # We grab the past memory (if any) and append the brand new question 
    past_messages = state.get("messages", []) 
    current_message = HumanMessage(content=state["user_query"]) 
    
    # We feed the System Persona + Past Memory + New Question to the LLM 
    messages_to_send = [system_prompt] + past_messages + [current_message] 
    
    response = llm.invoke(messages_to_send) 
    print(f"plan generated : {response.content}") 
    
    return {"messages": [current_message, response]}

# agent2 --> research agent =======================================================================
def researcher_agent(state: agent_state): 
    """Fetches live, unstructured data from the internet."""  
    current_count = state.get("search_count", 0) + 1 
    
    print("researcher agent : scraping data via search api's...") 
    
    # initialize the tavily client 
    tavily = TavilyClient() 
    
    # agent uses the user's original query to perform the search 
    search_query = state['user_query'] 
    print(f"executing search for : '{search_query}'") 
    
    # perform the search! we use advanced depth to get better quality snippets 
    search_response = tavily.search(query=search_query, search_depth="advanced") 
    
    # extract the actual result list from the response 
    results = search_response.get("results", []) 
    
    # print the title of the top result so that we can see it working in the terminal 
    if results: 
        print(f"top finding: {results[0]['title']}") 
        print(f"source: {results[0]['url']}") 
        
    # save the unstructured data to our shared state so the next agent can read it 
    return {
        "research_data": results, 
        "search_count": current_count, 
        "messages": ["research complete"]
    }
    
# agent3 --> verifier agent =================================================================
def verifier_agent(state: agent_state): 
    """Fact-checks the research against live data.""" 
    print('verifier agent: checking facts and evaluating sources...') 
    
    # escape hatch logic ---- 
    if state.get("search_count", 0) >= 3: 
        print("decision: max search attempts reached. forccing verification to proceed with best available data")
        return {"is_verified": True, "messages": ["verification complete: forced pass."]}
    
    user_query = state["user_query"] 
    research_data = state.get("research_data", []) 
    
    # create a strict prompt for the llm to evaluate the findings --
    eval_prompt = f""" 
    you are a strict verifier agent. 
    user's original query: '{user_query}'
    
    research data gathered by the researcher agent: 
    {research_data}
    
    does this research data contain enough relevant, up-to-date infor to accurately answer the 
    user's query ?
    
    respond with ONLY the word "YES" or "NO" 
    """
    
    # call the gemini brain to make the decision 
    response = llm.invoke(eval_prompt) 
    decision = response.content.strip().upper() 
    
    # update the state based on llm decision -- 
    if "YES" in decision:
        print("Decision:  Data is verified and sufficient.")
        return {"is_verified": True, "messages": ["Verification complete: Data approved."]}
    else:
        print("Decision: Data is insufficient. Sending back to Researcher.")
        return {"is_verified": False, "messages": ["Verification complete: Need more data."]}
     
# agent4 --> writer agent ======================================================================
def writer_agent(state: agent_state): 
    """Cleans and formats the verified data.""" 
    print("writer agent: structuring final response...") 
    
    user_query = state["user_query"] 
    research_data = state.get("research_data", []) 
    
    # Give the Writer a strict persona to format the output beautifully
    system_prompt = SystemMessage(
        content="You are an expert technical writer and AI assistant. Your job is to answer the user's query using ONLY the provided verified research data. "
                "Format your response beautifully using Markdown, clear headings, and bullet points. "
                "If the research data does not contain the answer, politely state that you could not find verified information."
    ) 
    
    # pass both  the original question and the live data we gathered 
    user_message = HumanMessage(
        content=f"user query: '{user_query}'\n\nverified research data:\n{research_data}"
    )
    
    # Call the Gemini Brain to write the final response
    response = llm.invoke([system_prompt, user_message]) 
    
    # print the final result beautifully in the terminal 
    print("\n" + "="*60)
    print("🎉 FINAL VERIFIED ANSWER:")
    print("="*60)
    print(response.content)
    print("="*60 + "\n")
    
    return {
        "final_output" : response.content, 
        "message": ["writing complete"]
    }

def should_continue(state: agent_state): 
    """ 
    decisions where to route the graph next based on verification state
    """ 
    if state["is_verified"]: 
        return "writer"
    else: 
        return "researcher" 
    

# building the graph -------------------
workflow = StateGraph(agent_state) 

# add our specialized agents as nodes 
workflow.add_node('intake', intake_agent) 
workflow.add_node('researcher', researcher_agent)
workflow.add_node('verifier', verifier_agent) 
workflow.add_node('writer', writer_agent) 

# define the flow (edges) 
workflow.set_entry_point('intake') 
workflow.add_edge('intake', 'researcher')
workflow.add_edge('researcher', 'verifier') 

# we add conditional logic here later:
# if verified, go to writer . if not verified, go back to researcher 

# using a conditional edge to create our reasoning loop 
workflow.add_conditional_edges(
    "verifier", 
    should_continue, 
    {
        "writer": "writer", 
        "researcher": "researcher"
    }
)

workflow.add_edge('writer', END) 

# memory checkpointer 
memory = MemorySaver() 

# compile the graph with memory 
app = workflow.compile(checkpointer=memory) 

# 4. test the skeleton ------------------ 

if __name__ == "__main__": 
    initial_state = {
        'messages': [], 
        'user_query': 'what are the latest breakthroughs in solid-state batteries??', 
        'search_count': 0, 
        'research_data': [], 
        'is_verified': False, 
        'final_output': ''
    } 
    
    print('--- starting multi-agent pipeline ---') 
    
    app.invoke(initial_state) 
    
    