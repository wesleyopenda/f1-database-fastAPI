from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.oauth2.id_token;
from google.auth.transport import requests
from google.cloud import firestore
import starlette.status as status

app = FastAPI()

firestore_db = firestore.Client()

firebase_request_adapter = requests.Request()

app.mount('/static', StaticFiles(directory = 'static'), name = 'static')
templates = Jinja2Templates(directory = "templates")

def getUser(user_token):
    user = firestore_db.collection('users').document(user_token['user_id'])
    if not user.get().exists:
        user_data = {
            'name': 'No name yet',
            'age': 0
        }
        firestore_db.collection('users').document(user_token['user_id']).set(user_data)
    return user

def validateFirebaseToken(id_token):
    if not id_token:
        return None
    
    user_token = None
    try:
        user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
    except ValueError as err:
        print(str(err))

    return user_token

@app.get("/", response_class=HTMLResponse)
async def root(request:Request):

    id_token = request.cookies.get("token")
    error_message = "No error here"

    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return templates.TemplateResponse('main.html', {'request' : request, 'user_token': None, 'error_message': None, 'user_info': None})

    user = getUser(user_token)
    return templates.TemplateResponse('main.html', {'request' : request, 'user_token': user_token, 'error_message': error_message, 'user_info': user.get()})

@app.get("/add-driver", response_class=HTMLResponse)
async def addDriver(request:Request):
    id_token = request.cookies.get("token")

    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/')
    
    user = getUser(user_token)
    return templates.TemplateResponse('add-driver.html', {'request' : request, 'user_token': user_token, 'error_message': None, 'user_info': user.get()})

@app.post("/add-driver")
async def addDriverPost(age: int = Form(...), pole_positions: int = Form(...), race_wins: int = Form(...), points_scored: int = Form(...), world_titles: int = Form(...), fastest_laps: int = Form(...), team: str = Form(...)):
    driver_data = {
        "Age": age,
        "Total Pole Positions": pole_positions,
        "Total Race Wins": race_wins,
        "Total Points Scored": points_scored,
        "Total World Titles": world_titles,
        "Total Fastest Laps": fastest_laps,
        "Team": team
    }
    firestore_db.collection("drivers").add(driver_data)
    return RedirectResponse('/add-driver', status_code=status.HTTP_302_FOUND)

@app.get("/add-team", response_class=HTMLResponse)
async def addTeam(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/')
    
    user = getUser(user_token)
    return templates.TemplateResponse('add-team.html', {'request' : request, 'user_token': user_token, 'error_message': None, 'user_info': user.get()})

@app.post("/add-team")
async def addTeamPost(year_founded: int = Form(...), team_pole_positions: int = Form(...), team_race_wins: int = Form(...), constructor_titles: int = Form(...), previous_season: int = Form(...)):
    team_data = {
        "Year Founded": year_founded,
        "Total Pole Positions": team_pole_positions,
        "Total Race Wins": team_race_wins,
        "Total Constructor Titles": constructor_titles,
        "Finishing Position in Previous Season": previous_season
    }
    firestore_db.collection("teams").add(team_data)
    return RedirectResponse('/add-team', status_code=status.HTTP_302_FOUND)

@app.get("/query-drivers", response_class=HTMLResponse)
async def queryDrivers(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/')
    
    user = getUser(user_token)
    return templates.TemplateResponse('query-drivers.html', {'request' : request, 'user_token': user_token, 'error_message': None, 'user_info': user.get()})

@app.post("/query-drivers")
async def queryDriversPost(attribute: str = Form(...), comparison: str = Form(...), value: int = Form(...)):
    
    drivers_ref = firestore_db.collection("drivers")

    if comparison == ">":
        query = drivers_ref.where(attribute, ">", value)
    elif comparison == "<":
        query = drivers_ref.where(attribute, "<", value)
    elif comparison == "==":
        query = drivers_ref.where(attribute, "==", value)
    else:
        return JSONResponse(content={"error": "Invalid comparison operator"}, status_code=400)

    results = [doc.to_dict() for doc in query.stream()]
    return JSONResponse(content={"drivers": results})

@app.get("/query-teams", response_class=HTMLResponse)
async def queryTeams(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/')
    
    user = getUser(user_token)
    return templates.TemplateResponse('query-teams.html', {'request' : request, 'user_token': user_token, 'error_message': None, 'user_info': user.get()})

@app.post("/query-teams")
async def queryTeamsPost(attribute: str = Form(...), comparison: str = Form(...), value: int = Form(...)):
    
    operator_map = {">": ">", "<": "<", "==": "=="}
    
    if comparison not in operator_map:
        return JSONResponse(content={"error": "Invalid comparison operator"}, status_code=400)

    teams_ref = firestore_db.collection("teams")
    query = teams_ref.where(attribute, operator_map[comparison], value)
    results = [doc.to_dict() for doc in query.stream()]

    return JSONResponse(content={"teams": results})