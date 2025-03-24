from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.oauth2.id_token;
from google.auth.transport import requests as google_requests
from google.cloud import firestore, storage
import starlette.status as status
import local_constants

app = FastAPI()

firestore_db = firestore.Client()

firebase_request_adapter = google_requests.Request()

app.mount('/static', StaticFiles(directory = 'static'), name = 'static')
templates = Jinja2Templates(directory = "templates")

def validate_firebase_token(id_token: str):
    if not id_token:
        return None
    try:
        token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        return token
    except ValueError as err:
        print(f"Token validation error: {err}")
        return None
    
def get_user(user_token):
    doc_ref = firestore_db.collection('users').document(user_token['user_id'])
    doc = doc_ref.get()
    if not doc.exists:
        # Create default user data if not present
        user_data = {
            "name": "John Doe",
            # Additional fields can be added here
        }
        doc_ref.set(user_data)
    return doc_ref

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    id_token = request.cookies.get("token")
    error_message = ""
    user_token = validate_firebase_token(id_token)
    user_info = None
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()

    return templates.TemplateResponse("main.html", {"request": request,"user_token": user_token,"error_message": error_message,"user_info": user_info,"drivers": [],"teams": []})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)

# -------------------------
# Driver Endpoints
# -------------------------

@app.get("/drivers", response_class=HTMLResponse)
async def list_drivers(request: Request):
    drivers_ref = firestore_db.collection("drivers")
    drivers = [doc.to_dict() | {"id": doc.id} for doc in drivers_ref.stream()]
    return templates.TemplateResponse("drivers_list.html", {"request": request, "drivers": drivers})

@app.get("/drivers/add", response_class=HTMLResponse)
async def add_driver_form(request: Request):
    return templates.TemplateResponse("add_driver.html", {"request": request})

@app.post("/drivers/add", response_class=RedirectResponse)
async def add_driver(
    request: Request,
    name: str = Form(...),
    age: int = Form(...),
    total_pole_positions: int = Form(...),
    total_race_wins: int = Form(...),
    total_points_scored: int = Form(...),
    total_world_titles: int = Form(...),
    total_fastest_laps: int = Form(...),
    team: str = Form(...),
    image: UploadFile = File(None)
):
    driver_data = {
        "name": name,
        "age": age,
        "total_pole_positions": total_pole_positions,
        "total_race_wins": total_race_wins,
        "total_points_scored": total_points_scored,
        "total_world_titles": total_world_titles,
        "total_fastest_laps": total_fastest_laps,
        "team": team,
        "image_url": None,
    }
    # Handle optional image upload
    if image is not None and image.filename != "":
        storage_client = storage.Client(project=local_constants.PROJECT_NAME)
        bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
        # Use a path that organizes driver images
        blob = bucket.blob(f"drivers/{image.filename}")
        blob.upload_from_file(image.file, content_type=image.content_type)
        driver_data["image_url"] = blob.public_url

    firestore_db.collection("drivers").add(driver_data)
    return RedirectResponse(url="/drivers", status_code=status.HTTP_302_FOUND)

@app.get("/drivers/{driver_id}", response_class=HTMLResponse)
async def driver_details(request: Request, driver_id: str):
    doc = firestore_db.collection("drivers").document(driver_id).get()
    if not doc.exists:
        return HTMLResponse("Driver not found", status_code=404)
    driver = doc.to_dict()
    driver["id"] = driver_id
    return templates.TemplateResponse("driver_details.html", {"request": request, "driver": driver})

@app.get("/drivers/edit/{driver_id}", response_class=HTMLResponse)
async def edit_driver_form(request: Request, driver_id: str):
    doc = firestore_db.collection("drivers").document(driver_id).get()
    if not doc.exists:
        return HTMLResponse("Driver not found", status_code=404)
    driver = doc.to_dict()
    driver["id"] = driver_id
    return templates.TemplateResponse("edit_driver.html", {"request": request, "driver": driver})

@app.post("/drivers/edit/{driver_id}", response_class=RedirectResponse)
async def edit_driver(
    request: Request,
    driver_id: str,
    name: str = Form(...),
    age: int = Form(...),
    total_pole_positions: int = Form(...),
    total_race_wins: int = Form(...),
    total_points_scored: int = Form(...),
    total_world_titles: int = Form(...),
    total_fastest_laps: int = Form(...),
    team: str = Form(...),
    image: UploadFile = File(None)
):
    driver_data = {
        "name": name,
        "age": age,
        "total_pole_positions": total_pole_positions,
        "total_race_wins": total_race_wins,
        "total_points_scored": total_points_scored,
        "total_world_titles": total_world_titles,
        "total_fastest_laps": total_fastest_laps,
        "team": team,
    }
    if image is not None and image.filename != "":
        storage_client = storage.Client(project=local_constants.PROJECT_NAME)
        bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
        blob = bucket.blob(f"drivers/{image.filename}")
        blob.upload_from_file(image.file, content_type=image.content_type)
        driver_data["image_url"] = blob.public_url

    firestore_db.collection("drivers").document(driver_id).update(driver_data)
    return RedirectResponse(url=f"/drivers/{driver_id}", status_code=status.HTTP_302_FOUND)

@app.post("/drivers/delete/{driver_id}", response_class=RedirectResponse)
async def delete_driver(driver_id: str):
    firestore_db.collection("drivers").document(driver_id).delete()
    return RedirectResponse(url="/drivers", status_code=status.HTTP_302_FOUND)

# -------------------------
# Team Endpoints
# -------------------------

@app.get("/teams", response_class=HTMLResponse)
async def list_teams(request: Request):
    # Query all teams from the "teams" collection
    teams_ref = firestore_db.collection("teams")
    teams = [doc.to_dict() | {"id": doc.id} for doc in teams_ref.stream()]
    return templates.TemplateResponse("teams_list.html", {"request": request, "teams": teams})

@app.get("/teams/add", response_class=HTMLResponse)
async def add_team_form(request: Request):
    return templates.TemplateResponse("add_team.html", {"request": request})

@app.post("/teams/add", response_class=RedirectResponse)
async def add_team(
    request: Request,
    name: str = Form(...),
    year_founded: int = Form(...),
    total_pole_positions: int = Form(...),
    total_race_wins: int = Form(...),
    total_constructor_titles: int = Form(...),
    finishing_position_previous_season: int = Form(...),
    logo: UploadFile = File(None)
):
    team_data = {
        "name": name,
        "year_founded": year_founded,
        "total_pole_positions": total_pole_positions,
        "total_race_wins": total_race_wins,
        "total_constructor_titles": total_constructor_titles,
        "finishing_position_previous_season": finishing_position_previous_season,
        "logo_url": None,
    }
    # Handle optional logo upload
    if logo is not None and logo.filename != "":
        storage_client = storage.Client(project=local_constants.PROJECT_NAME)
        bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
        blob = bucket.blob(f"teams/{logo.filename}")
        blob.upload_from_file(logo.file, content_type=logo.content_type)
        team_data["logo_url"] = blob.public_url

    firestore_db.collection("teams").add(team_data)
    return RedirectResponse(url="/teams", status_code=status.HTTP_302_FOUND)

@app.get("/teams/{team_id}", response_class=HTMLResponse)
async def team_details(request: Request, team_id: str):
    doc = firestore_db.collection("teams").document(team_id).get()
    if not doc.exists:
        return HTMLResponse("Team not found", status_code=404)
    team = doc.to_dict()
    team["id"] = team_id

    # Query drivers associated with this team. We assume driver documents have a "team" field.
    drivers_ref = firestore_db.collection("drivers").where("team", "==", team["name"])
    drivers = [doc.to_dict() | {"id": doc.id} for doc in drivers_ref.stream()]

    return templates.TemplateResponse("team_details.html", {
        "request": request,
        "team": team,
        "drivers": drivers  # List of drivers for this team
    })

@app.get("/teams/edit/{team_id}", response_class=HTMLResponse)
async def edit_team_form(request: Request, team_id: str):
    doc = firestore_db.collection("teams").document(team_id).get()
    if not doc.exists:
        return HTMLResponse("Team not found", status_code=404)
    team = doc.to_dict()
    team["id"] = team_id
    return templates.TemplateResponse("edit_team.html", {"request": request, "team": team})

@app.post("/teams/edit/{team_id}", response_class=RedirectResponse)
async def edit_team(
    request: Request,
    team_id: str,
    name: str = Form(...),
    year_founded: int = Form(...),
    total_pole_positions: int = Form(...),
    total_race_wins: int = Form(...),
    total_constructor_titles: int = Form(...),
    finishing_position_previous_season: int = Form(...),
    logo: UploadFile = File(None)
):
    team_data = {
        "name": name,
        "year_founded": year_founded,
        "total_pole_positions": total_pole_positions,
        "total_race_wins": total_race_wins,
        "total_constructor_titles": total_constructor_titles,
        "finishing_position_previous_season": finishing_position_previous_season,
    }
    if logo is not None and logo.filename != "":
        storage_client = storage.Client(project=local_constants.PROJECT_NAME)
        bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
        blob = bucket.blob(f"teams/{logo.filename}")
        blob.upload_from_file(logo.file, content_type=logo.content_type)
        team_data["logo_url"] = blob.public_url

    firestore_db.collection("teams").document(team_id).update(team_data)
    return RedirectResponse(url=f"/teams/{team_id}", status_code=status.HTTP_302_FOUND)

@app.post("/teams/delete/{team_id}", response_class=RedirectResponse)
async def delete_team(team_id: str):
    firestore_db.collection("teams").document(team_id).delete()
    return RedirectResponse(url="/teams", status_code=status.HTTP_302_FOUND)

# -------------------------
# Comparison Endpoints
# -------------------------

# Driver Comparison

@app.get("/compare/drivers", response_class=HTMLResponse)
async def compare_drivers_form(request: Request):
    # Get list of drivers for dropdowns
    drivers_ref = firestore_db.collection("drivers")
    drivers = [doc.to_dict() | {"id": doc.id} for doc in drivers_ref.stream()]
    return templates.TemplateResponse("compare_drivers_form.html", {"request": request, "drivers": drivers})

@app.post("/compare/drivers", response_class=HTMLResponse)
async def compare_drivers(
    request: Request,
    driver1_id: str = Form(...),
    driver2_id: str = Form(...)
):
    # Retrieve driver documents
    doc1 = firestore_db.collection("drivers").document(driver1_id).get()
    doc2 = firestore_db.collection("drivers").document(driver2_id).get()
    if not doc1.exists or not doc2.exists:
        return HTMLResponse("One or both drivers not found", status_code=404)
    driver1 = doc1.to_dict()
    driver2 = doc2.to_dict()

    # Compare key statistics:
    # For age, lower is better; for all others, higher is better.
    stats = ["age", "total_pole_positions", "total_race_wins", "total_points_scored", "total_world_titles", "total_fastest_laps"]
    comparison = []
    for stat in stats:
        value1 = driver1.get(stat, 0)
        value2 = driver2.get(stat, 0)
        if stat == "age":
            if value1 < value2:
                better = "driver1"
            elif value2 < value1:
                better = "driver2"
            else:
                better = "equal"
        else:
            if value1 > value2:
                better = "driver1"
            elif value2 > value1:
                better = "driver2"
            else:
                better = "equal"
        comparison.append({
            "stat": stat,
            "driver1_value": value1,
            "driver2_value": value2,
            "better": better
        })
    return templates.TemplateResponse("compare_drivers.html", {
        "request": request,
        "driver1": driver1,
        "driver2": driver2,
        "comparison": comparison
    })

# Team Comparison

@app.get("/compare/teams", response_class=HTMLResponse)
async def compare_teams_form(request: Request):
    teams_ref = firestore_db.collection("teams")
    teams = [doc.to_dict() | {"id": doc.id} for doc in teams_ref.stream()]
    return templates.TemplateResponse("compare_teams_form.html", {"request": request, "teams": teams})

@app.post("/compare/teams", response_class=HTMLResponse)
async def compare_teams(
    request: Request,
    team1_id: str = Form(...),
    team2_id: str = Form(...)
):
    doc1 = firestore_db.collection("teams").document(team1_id).get()
    doc2 = firestore_db.collection("teams").document(team2_id).get()
    if not doc1.exists or not doc2.exists:
        return HTMLResponse("One or both teams not found", status_code=404)
    team1 = doc1.to_dict()
    team2 = doc2.to_dict()

    # For teams, assume these fields:
    # year_founded and finishing_position_previous_season: lower is better;
    # total_pole_positions, total_race_wins, total_constructor_titles: higher is better.
    stats = ["year_founded", "total_pole_positions", "total_race_wins", "total_constructor_titles", "finishing_position_previous_season"]
    comparison = []
    for stat in stats:
        value1 = team1.get(stat, 0)
        value2 = team2.get(stat, 0)
        if stat in ["year_founded", "finishing_position_previous_season"]:
            if value1 < value2:
                better = "team1"
            elif value2 < value1:
                better = "team2"
            else:
                better = "equal"
        else:
            if value1 > value2:
                better = "team1"
            elif value2 > value1:
                better = "team2"
            else:
                better = "equal"
        comparison.append({
            "stat": stat,
            "team1_value": value1,
            "team2_value": value2,
            "better": better
        })
    return templates.TemplateResponse("compare_teams.html", {
        "request": request,
        "team1": team1,
        "team2": team2,
        "comparison": comparison
    })
