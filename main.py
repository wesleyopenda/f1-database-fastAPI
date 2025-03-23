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
        "Total_Pole_Positions": pole_positions,
        "Total_Race_Wins": race_wins,
        "Total_Points_Scored": points_scored,
        "Total_World_Titles": world_titles,
        "Total_Fastest_Laps": fastest_laps,
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
async def addTeamPost(team_name: str = Form(...) ,year_founded: int = Form(...), team_pole_positions: int = Form(...), team_race_wins: int = Form(...), constructor_titles: int = Form(...), previous_season: int = Form(...)):
    team_data = {
        "Team_Name": team_name,
        "Year-Founded": year_founded,
        "Total_Pole_Positions": team_pole_positions,
        "Total_Race_Wins": team_race_wins,
        "Total_Constructor_Titles": constructor_titles,
        "Finishing_Position_in_Previous_Season": previous_season
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

    teams_ref = firestore_db.collection("teams")

    if comparison == ">":
        query = teams_ref.where(attribute, ">", value)
    elif comparison == "<":
        query = teams_ref.where(attribute, "<", value)
    elif comparison == "==":
        query = teams_ref.where(attribute, "==", value)
    else:
        return JSONResponse(content={"error": "Invalid comparison operator"}, status_code=400)

    results = [doc.to_dict() for doc in query.stream()]
    return JSONResponse(content={"teams": results})

@app.get("/compare-drivers", response_class=HTMLResponse)
async def compareDrivers(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/')
    
    user = getUser(user_token)
    return templates.TemplateResponse('compare-drivers.html', {'request' : request, 'user_token': user_token, 'error_message': None, 'user_info': user.get()})

@app.post("/compare-drivers")
async def compareDriversPost(driver1: str = Form(...), driver2: str = Form(...)):
    driver1_doc = firestore_db.collection("drivers").where("name", "==", driver1).get()
    driver2_doc = firestore_db.collection("drivers").where("name", "==", driver2).get()

    if not driver1_doc or not driver2_doc:
        return JSONResponse(content={"error": "One or both drivers not found"}, status_code=400)

    driver1_data = driver1_doc[0].to_dict()
    driver2_data = driver2_doc[0].to_dict()

    comparison = {}
    for stat in driver1_data.keys():
        if isinstance(driver1_data[stat], int):
            better = "driver1" if driver1_data[stat] > driver2_data[stat] else "driver2"
            if stat == "Age":
                better = "driver1" if driver1_data[stat] < driver2_data[stat] else "driver2"
            comparison[stat] = {"driver1": driver1_data[stat], "driver2": driver2_data[stat], "better": better}

    return JSONResponse(content={"comparison": comparison})

@app.get("/compare-teams", response_class=HTMLResponse)
async def compareTeams(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return RedirectResponse('/')
    
    user = getUser(user_token)
    return templates.TemplateResponse('compare-teams.html', {'request' : request, 'user_token': user_token, 'error_message': None, 'user_info': user.get()})

@app.post("/compare-teams")
async def compareTeamsPost(team1: str = Form(...), team2: str = Form(...)):
    team1_doc = firestore_db.collection("teams").where("name", "==", team1).get()
    team2_doc = firestore_db.collection("teams").where("name", "==", team2).get()

    if not team1_doc or not team2_doc:
        return JSONResponse(content={"error": "One or both teams not found"}, status_code=400)

    team1_data = team1_doc[0].to_dict()
    team2_data = team2_doc[0].to_dict()

    comparison = {}
    for stat in team1_data.keys():
        if isinstance(team1_data[stat], int):
            better = "team1" if team1_data[stat] > team2_data[stat] else "team2"
            if stat in ["Finishing Position in Previous Season", "Year Founded"]:
                better = "team1" if team1_data[stat] < team2_data[stat] else "team2"
            comparison[stat] = {"team1": team1_data[stat], "team2": team2_data[stat], "better": better}

    return JSONResponse(content={"comparison": comparison})