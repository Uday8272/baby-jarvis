
from fastapi import FastAPI 
from fastapi.responses import HTMLResponse 
from pydantic import BaseModel 
from main import app as agent_app 

# initialize fastapi application 
app = FastAPI(title="jarvis") 

# define the structure of the data we expect from the frontend 
class query_request(BaseModel): 
    query: str 
    
# 1. the api endpoint: this is where the frontend sends the user's question 
@app.post("/api/research") 
async def run_research(request: query_request):
    
    initial_state = {
        "messages": [], 
        "user_query": request.query, 
        "search_count": 0,
        "research_data": [], 
        "is_verified": False, 
        "final_output": ''
    } 
    
    # run your multu-agent pipeline 
    result = agent_app.invoke(initial_state) 
    
    # return only the beautifully formatted markdown from the writer agent 
    return {"result": result["final_output"]} 

# 2. the ui endpoint: this serves our beautiful html interface 
@app.get("/", response_class=HTMLResponse) 
async def get_ui(): 
    with open("index.html", "r", encoding="utf-8") as f: 
        return f.read() 
    
    