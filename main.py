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

