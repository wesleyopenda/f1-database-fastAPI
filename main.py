from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.oauth2.id_token
from google.auth.transport import requests as google_requests
from google.cloud import firestore, storage
import starlette.status as status
import local_constants

app = FastAPI()

firestore_db = firestore.Client()
firebase_request_adapter = google_requests.Request()

app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory="templates")

def get_user(user_token):
    doc_ref = firestore_db.collection('users').document(user_token['user_id'])
    doc = doc_ref.get()
    if not doc.exists:
        # Create default user data if not present, using the token's email if available.
        user_data = {
            "name": user_token.get("email", "John Doe"),
            "email": user_token.get("email", "Unknown")
        }
        doc_ref.set(user_data)
    return doc_ref

def validate_firebase_token(id_token: str):
    if not id_token:
        return None
    try:
        user_token = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        return user_token
    except ValueError as err:
        print(f"Token validation error: {err}")
        return None

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    id_token = request.cookies.get("token")
    error_message = ""
    user_token = validate_firebase_token(id_token)
    user_info = {}

    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        # Ensure that user_token includes an 'email' key using the Firestore user document.
        user_token["email"] = user_info.get("email", "Unknown")

    # Query pre-installed drivers from Firestore
    drivers_ref = firestore_db.collection("drivers")
    drivers = []
    for doc in drivers_ref.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        drivers.append(d)

    # Query pre-installed teams from Firestore
    teams_ref = firestore_db.collection("teams")
    teams = []
    for doc in teams_ref.stream():
        t = doc.to_dict()
        t["id"] = doc.id
        teams.append(t)

    print(f"DEBUG: Found {len(drivers)} drivers and {len(teams)} teams")

    return templates.TemplateResponse("main.html", {
        "request": request,
        "user_token": user_token,
        "error_message": error_message,
        "user_info": user_info,
        "drivers": drivers,
        "teams": teams
    })

# -------------------------
# Authentication Endpoints
# -------------------------

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        return RedirectResponse("/")
    return templates.TemplateResponse("login.html", {"request": request, "user_token": user_token})

# Remove separate signup endpoint to use a single auth page.
# @app.get("/signup", response_class=HTMLResponse)
# async def signup_page(request: Request):
#     return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/logout", response_class=RedirectResponse)
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("token")
    return response

# -------------------------
# Driver Endpoints
# -------------------------

@app.get("/drivers", response_class=HTMLResponse)
async def list_drivers(request: Request):
    # Retrieve and validate token
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        user_token["email"] = user_info.get("email", "Unknown")
    else:
        user_token = None

    drivers_ref = firestore_db.collection("drivers")
    drivers = []
    for doc in drivers_ref.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        drivers.append(d)
    
    return templates.TemplateResponse("drivers_list.html", {"request": request,"drivers": drivers,"user_token": user_token})

@app.get("/drivers/query", response_class=HTMLResponse)
async def query_drivers_form(request: Request):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        user_token["email"] = user_info.get("email", "Unknown")
    else:
        user_token = None
    return templates.TemplateResponse("query_drivers.html", {"request": request, "user_token": user_token})

@app.post("/drivers/query", response_class=HTMLResponse)
async def query_drivers(request: Request, attribute: str = Form(...), operator: str = Form(...), value: str = Form(...)):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        user_token["email"] = user_info.get("email", "Unknown")
    else:
        user_token = None

    drivers_ref = firestore_db.collection("drivers")
    if attribute in ["age", "total_pole_positions", "total_race_wins", "total_points_scored", "total_world_titles", "total_fastest_laps"]:
        try:
            value = int(value)
        except ValueError:
            return HTMLResponse("Invalid numeric value provided.", status_code=400)
    query = drivers_ref.where(attribute, operator, value)
    drivers = []
    for doc in query.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        drivers.append(d)
    context = {"request": request, "drivers": drivers, "user_token": user_token}
    if not drivers:
        context["message"] = "No drivers found matching your query."
    return templates.TemplateResponse("drivers_list.html", context)


@app.get("/drivers/add", response_class=HTMLResponse)
async def add_driver_form(request: Request):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        user_token["email"] = user_info.get("email", "Unknown")
    else:
        user_token = None
    return templates.TemplateResponse("add_driver.html", {"request": request, "user_token": user_token})


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
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if not user_token:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    existing_drivers = list(firestore_db.collection("drivers").where("name", "==", name).stream())
    if existing_drivers:
        return HTMLResponse("Driver with the same name already exists.", status_code=400)

    if image is not None and image.filename != "":
        image.file.seek(0)
        storage_client = storage.Client(project=local_constants.PROJECT_NAME)
        bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
        blob = bucket.blob(f"drivers/{image.filename}")
        blob.upload_from_file(image.file, content_type=image.content_type)
        blob.make_public()
        image_url = blob.public_url
    else:
        image_url = "https://storage.googleapis.com/assignment01-453218.appspot.com/placeholder.png"

    driver_data = {
        "name": name,
        "age": age,
        "total_pole_positions": total_pole_positions,
        "total_race_wins": total_race_wins,
        "total_points_scored": total_points_scored,
        "total_world_titles": total_world_titles,
        "total_fastest_laps": total_fastest_laps,
        "team": team,
        "image_url": image_url,
    }

    firestore_db.collection("drivers").add(driver_data)
    return RedirectResponse(url="/drivers", status_code=status.HTTP_302_FOUND)

@app.get("/drivers/{driver_id}", response_class=HTMLResponse)
async def driver_details(request: Request, driver_id: str):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        user_token["email"] = user_info.get("email", "Unknown")
    else:
        user_token = None
    doc = firestore_db.collection("drivers").document(driver_id).get()
    if not doc.exists:
        return HTMLResponse("Driver not found", status_code=404)
    driver = doc.to_dict()
    driver["id"] = driver_id
    return templates.TemplateResponse("driver_details.html", {"request": request, "driver": driver, "user_token": user_token})


@app.get("/drivers/edit/{driver_id}", response_class=HTMLResponse)
async def edit_driver_form(request: Request, driver_id: str):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        user_token["email"] = user_info.get("email", "Unknown")
    else:
        user_token = None
    doc = firestore_db.collection("drivers").document(driver_id).get()
    if not doc.exists:
        return HTMLResponse("Driver not found", status_code=404)
    driver = doc.to_dict()
    driver["id"] = driver_id
    return templates.TemplateResponse("edit_driver.html", {"request": request, "driver": driver, "user_token": user_token})


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
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if not user_token:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    duplicate_drivers = [
        doc for doc in firestore_db.collection("drivers").where("name", "==", name).stream()
        if doc.id != driver_id
    ]
    if duplicate_drivers:
        return HTMLResponse("Driver with the same name already exists.", status_code=400)

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
        image.file.seek(0)
        storage_client = storage.Client(project=local_constants.PROJECT_NAME)
        bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
        blob = bucket.blob(f"drivers/{image.filename}")
        blob.upload_from_file(image.file, content_type=image.content_type)
        blob.make_public()
        driver_data["image_url"] = blob.public_url

    firestore_db.collection("drivers").document(driver_id).update(driver_data)
    return RedirectResponse(url=f"/drivers/{driver_id}", status_code=status.HTTP_302_FOUND)

@app.post("/drivers/delete/{driver_id}", response_class=RedirectResponse)
async def delete_driver(driver_id: str, request: Request):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if not user_token:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    driver_ref = firestore_db.collection("drivers").document(driver_id)
    driver_doc = driver_ref.get()
    if driver_doc.exists:
        driver = driver_doc.to_dict()
        image_url = driver.get("image_url")
        if image_url and "placeholder_driver.jpg" not in image_url:
            from urllib.parse import urlparse
            parsed_url = urlparse(image_url)
            file_path = parsed_url.path.lstrip('/')
            try:
                storage_client = storage.Client(project=local_constants.PROJECT_NAME)
                bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
                blob = bucket.blob(file_path)
                blob.delete()
                print("Deleted image:", image_url)
            except Exception as e:
                print("Error deleting image:", e)
    driver_ref.delete()
    return RedirectResponse(url="/drivers", status_code=status.HTTP_302_FOUND)

# -------------------------
# Team Endpoints
# -------------------------

@app.get("/teams", response_class=HTMLResponse)
async def list_teams(request: Request):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        user_token["email"] = user_info.get("email", "Unknown")
    else:
        user_token = None
    teams_ref = firestore_db.collection("teams")
    teams = []
    for doc in teams_ref.stream():
        t = doc.to_dict()
        t["id"] = doc.id
        teams.append(t)
    return templates.TemplateResponse("teams_list.html", {"request": request, "teams": teams, "user_token": user_token})


@app.get("/teams/query", response_class=HTMLResponse)
async def query_teams_form(request: Request):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        user_token["email"] = user_info.get("email", "Unknown")
    else:
        user_token = None
    return templates.TemplateResponse("query_teams.html", {"request": request, "user_token": user_token})


@app.post("/teams/query", response_class=HTMLResponse)
async def query_teams(request: Request, attribute: str = Form(...), operator: str = Form(...), value: str = Form(...)):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        user_token["email"] = user_info.get("email", "Unknown")
    else:
        user_token = None

    teams_ref = firestore_db.collection("teams")
    if attribute in ["year_founded", "total_pole_positions", "total_race_wins", "total_constructor_titles", "finishing_position_previous_season"]:
        try:
            value = int(value)
        except ValueError:
            return HTMLResponse("Invalid numeric value provided.", status_code=400)
    query = teams_ref.where(attribute, operator, value)
    teams = []
    for doc in query.stream():
        t = doc.to_dict()
        t["id"] = doc.id
        teams.append(t)
    context = {"request": request, "teams": teams, "user_token": user_token}
    if not teams:
        context["message"] = "No teams found matching your query."
    return templates.TemplateResponse("teams_list.html", context)


@app.get("/teams/add", response_class=HTMLResponse)
async def add_team_form(request: Request):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        user_token["email"] = user_info.get("email", "Unknown")
    else:
        user_token = None
    return templates.TemplateResponse("add_team.html", {"request": request, "user_token": user_token})


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
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if not user_token:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    existing_teams = list(firestore_db.collection("teams").where("name", "==", name).stream())
    if existing_teams:
        return HTMLResponse("Team with the same name already exists.", status_code=400)
    
    if logo is not None and logo.filename != "":
        try:
            logo.file.seek(0)
            storage_client = storage.Client(project=local_constants.PROJECT_NAME)
            bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
            blob = bucket.blob(f"teams/{logo.filename}")
            blob.upload_from_file(logo.file, content_type=logo.content_type)
            blob.make_public()
            logo_url = blob.public_url
        except Exception as e:
            print("Error uploading logo:", e)
            return HTMLResponse("Error uploading logo.", status_code=500)
    else:
        logo_url = "https://storage.googleapis.com/assignment01-453218.appspot.com/placeholder-team.png"
    
    team_data = {
        "name": name,
        "year_founded": year_founded,
        "total_pole_positions": total_pole_positions,
        "total_race_wins": total_race_wins,
        "total_constructor_titles": total_constructor_titles,
        "finishing_position_previous_season": finishing_position_previous_season,
        "logo_url": logo_url,
    }
    
    firestore_db.collection("teams").add(team_data)
    return RedirectResponse(url="/teams", status_code=status.HTTP_302_FOUND)

@app.get("/teams/{team_id}", response_class=HTMLResponse)
async def team_details(request: Request, team_id: str):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        user_token["email"] = user_info.get("email", "Unknown")
    else:
        user_token = None
    doc = firestore_db.collection("teams").document(team_id).get()
    if not doc.exists:
        return HTMLResponse("Team not found", status_code=404)
    team = doc.to_dict()
    team["id"] = team_id

    drivers_ref = firestore_db.collection("drivers").where("team", "==", team["name"])
    drivers = []
    for doc in drivers_ref.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        drivers.append(d)
    return templates.TemplateResponse("team_details.html", {"request": request, "team": team, "drivers": drivers, "user_token": user_token})


@app.get("/teams/edit/{team_id}", response_class=HTMLResponse)
async def edit_team_form(request: Request, team_id: str):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        user_token["email"] = user_info.get("email", "Unknown")
    else:
        user_token = None
    doc = firestore_db.collection("teams").document(team_id).get()
    if not doc.exists:
        return HTMLResponse("Team not found", status_code=404)
    team = doc.to_dict()
    team["id"] = team_id
    return templates.TemplateResponse("edit_team.html", {"request": request, "team": team, "user_token": user_token})


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
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if not user_token:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    duplicate_teams = [
        doc for doc in firestore_db.collection("teams").where("name", "==", name).stream()
        if doc.id != team_id
    ]
    if duplicate_teams:
        return HTMLResponse("Team with the same name already exists.", status_code=400)

    team_data = {
        "name": name,
        "year_founded": year_founded,
        "total_pole_positions": total_pole_positions,
        "total_race_wins": total_race_wins,
        "total_constructor_titles": total_constructor_titles,
        "finishing_position_previous_season": finishing_position_previous_season,
    }

    if logo is not None and logo.filename != "":
        logo.file.seek(0)
        storage_client = storage.Client(project=local_constants.PROJECT_NAME)
        bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
        blob = bucket.blob(f"teams/{logo.filename}")
        blob.upload_from_file(logo.file, content_type=logo.content_type)
        blob.make_public()
        team_data["logo_url"] = blob.public_url

    firestore_db.collection("teams").document(team_id).update(team_data)
    return RedirectResponse(url=f"/teams/{team_id}", status_code=status.HTTP_302_FOUND)

@app.post("/teams/delete/{team_id}", response_class=RedirectResponse)
async def delete_team(team_id: str, request: Request):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if not user_token:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    team_ref = firestore_db.collection("teams").document(team_id)
    team_doc = team_ref.get()
    if team_doc.exists:
        team = team_doc.to_dict()
        logo_url = team.get("logo_url")
        if logo_url and "placeholder_team.jpg" not in logo_url:
            from urllib.parse import urlparse
            parsed_url = urlparse(logo_url)
            file_path = parsed_url.path.lstrip('/')
            try:
                storage_client = storage.Client(project=local_constants.PROJECT_NAME)
                bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
                blob = bucket.blob(file_path)
                blob.delete()
                print("Deleted logo:", logo_url)
            except Exception as e:
                print("Error deleting logo:", e)
    team_ref.delete()
    return RedirectResponse(url="/teams", status_code=status.HTTP_302_FOUND)

# -------------------------
# Comparison Endpoints
# -------------------------

@app.get("/compare/drivers", response_class=HTMLResponse)
async def compare_drivers_form(request: Request):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        user_token["email"] = user_info.get("email", "Unknown")
    else:
        user_token = None

    drivers_ref = firestore_db.collection("drivers")
    drivers = [doc.to_dict() | {"id": doc.id} for doc in drivers_ref.stream()]
    return templates.TemplateResponse("compare_drivers_form.html", {"request": request,"drivers": drivers,"user_token": user_token})

@app.post("/compare/drivers", response_class=HTMLResponse)
async def compare_drivers(
    request: Request,
    driver1_id: str = Form(...),
    driver2_id: str = Form(...)
):
    if driver1_id == driver2_id:
        return HTMLResponse("Please select two different drivers for comparison.", status_code=400)
    
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        user_token["email"] = user_info.get("email", "Unknown")
    else:
        user_token = None

    doc1 = firestore_db.collection("drivers").document(driver1_id).get()
    doc2 = firestore_db.collection("drivers").document(driver2_id).get()
    if not doc1.exists or not doc2.exists:
        return HTMLResponse("One or both drivers not found", status_code=404)
    driver1 = doc1.to_dict()
    driver2 = doc2.to_dict()

    stats = ["age", "total_pole_positions", "total_race_wins", "total_points_scored", "total_world_titles", "total_fastest_laps"]
    comparison = []
    for stat in stats:
        value1 = driver1.get(stat, 0)
        value2 = driver2.get(stat, 0)
        # For age, lower is better; for others, higher is better.
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
        comparison.append({"stat": stat,"driver1_value": value1,"driver2_value": value2,"better": better})

    return templates.TemplateResponse("compare_drivers.html", {"request": request,"driver1": driver1,"driver2": driver2,"comparison": comparison,"user_token": user_token})


@app.get("/compare/teams", response_class=HTMLResponse)
async def compare_teams_form(request: Request):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        user_token["email"] = user_info.get("email", "Unknown")
    else:
        user_token = None

    teams_ref = firestore_db.collection("teams")
    teams = [doc.to_dict() | {"id": doc.id} for doc in teams_ref.stream()]
    return templates.TemplateResponse("compare_teams_form.html", {"request": request,"teams": teams,"user_token": user_token})


@app.post("/compare/teams", response_class=HTMLResponse)
async def compare_teams(
    request: Request,
    team1_id: str = Form(...),
    team2_id: str = Form(...)
):
    if team1_id == team2_id:
        return HTMLResponse("Please select two different teams for comparison.", status_code=400)
    
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if user_token:
        user_doc = get_user(user_token)
        user_info = user_doc.get().to_dict()
        user_token["email"] = user_info.get("email", "Unknown")
    else:
        user_token = None

    doc1 = firestore_db.collection("teams").document(team1_id).get()
    doc2 = firestore_db.collection("teams").document(team2_id).get()
    if not doc1.exists or not doc2.exists:
        return HTMLResponse("One or both teams not found", status_code=404)
    team1 = doc1.to_dict()
    team2 = doc2.to_dict()

    stats = ["year_founded", "total_pole_positions", "total_race_wins", "total_constructor_titles", "finishing_position_previous_season"]
    comparison = []
    for stat in stats:
        value1 = team1.get(stat, 0)
        value2 = team2.get(stat, 0)
        # For teams, lower is better for year_founded and finishing_position_previous_season; higher is better for others.
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
        comparison.append({"stat": stat,"team1_value": value1,"team2_value": value2,"better": better})

    return templates.TemplateResponse("compare_teams.html", {"request": request,"team1": team1,"team2": team2,"comparison": comparison,"user_token": user_token})


def seed_sample_data():
    # Seed sample drivers if none exist
    drivers_ref = firestore_db.collection("drivers")
    if not any(drivers_ref.stream()):
        sample_drivers = [
            {
                "name": "Lewis Hamilton",
                "age": 37,
                "total_pole_positions": 100,
                "total_race_wins": 104,
                "total_points_scored": 5000,
                "total_world_titles": 7,
                "total_fastest_laps": 50,
                "team": "Ferrari",
                "image_url": "https://storage.googleapis.com/assignment01-453218.appspot.com/lewis.png",
            },
            {
                "name": "Max Verstappen",
                "age": 25,
                "total_pole_positions": 60,
                "total_race_wins": 50,
                "total_points_scored": 3000,
                "total_world_titles": 2,
                "total_fastest_laps": 30,
                "team": "Red Bull",
                "image_url": "https://storage.googleapis.com/assignment01-453218.appspot.com/max.png",
            },
            {
                "name": "Charles Leclerc",
                "age": 26,
                "total_pole_positions": 20,
                "total_race_wins": 5,
                "total_points_scored": 1200,
                "total_world_titles": 0,
                "total_fastest_laps": 10,
                "team": "Ferrari",
                "image_url": "https://storage.googleapis.com/assignment01-453218.appspot.com/leclerc.png",
            },
            {
                "name": "Lando Norris",
                "age": 23,
                "total_pole_positions": 5,
                "total_race_wins": 4,
                "total_points_scored": 800,
                "total_world_titles": 0,
                "total_fastest_laps": 10,
                "team": "McClaren",
                "image_url": "https://storage.googleapis.com/assignment01-453218.appspot.com/norris.png",
            },
            {
                "name": "George Russel",
                "age": 24,
                "total_pole_positions": 3,
                "total_race_wins": 2,
                "total_points_scored": 900,
                "total_world_titles": 0,
                "total_fastest_laps": 6,
                "team": "Mercedes",
                "image_url": "https://storage.googleapis.com/assignment01-453218.appspot.com/russel.png",
            },
            {
                "name": "Alex Albon",
                "age": 25,
                "total_pole_positions": 1,
                "total_race_wins": 2,
                "total_points_scored": 850,
                "total_world_titles": 0,
                "total_fastest_laps": 3,
                "team": "Williams",
                "image_url": "https://storage.googleapis.com/assignment01-453218.appspot.com/albon.png",
            },
        ]
        for driver in sample_drivers:
            firestore_db.collection("drivers").add(driver)

    # Seed sample teams if none exist
    teams_ref = firestore_db.collection("teams")
    if not any(teams_ref.stream()):
        sample_teams = [
            {
                "name": "Mercedes",
                "year_founded": 1954,
                "total_pole_positions": 150,
                "total_race_wins": 120,
                "total_constructor_titles": 8,
                "finishing_position_previous_season": 1,
                "logo_url": "https://storage.googleapis.com/assignment01-453218.appspot.com/Mercedes.png",
            },
            {
                "name": "Red Bull",
                "year_founded": 2005,
                "total_pole_positions": 100,
                "total_race_wins": 90,
                "total_constructor_titles": 4,
                "finishing_position_previous_season": 2,
                "logo_url": "https://storage.googleapis.com/assignment01-453218.appspot.com/red-bull.jpg",
            },
            {
                "name": "Ferrari",
                "year_founded": 1929,
                "total_pole_positions": 130,
                "total_race_wins": 110,
                "total_constructor_titles": 16,
                "finishing_position_previous_season": 3,
                "logo_url": "https://storage.googleapis.com/assignment01-453218.appspot.com/Ferrari.png",
            },
            {
                "name": "Mclaren",
                "year_founded": 1963,
                "total_pole_positions": 164,
                "total_race_wins": 191,
                "total_constructor_titles": 9,
                "finishing_position_previous_season": 1,
                "logo_url": "https://storage.googleapis.com/assignment01-453218.appspot.com/Mclaren.png",
            },
            {
                "name": "Williams",
                "year_founded": 1985,
                "total_pole_positions": 100,
                "total_race_wins": 30,
                "total_constructor_titles": 2,
                "finishing_position_previous_season": 10,
                "logo_url": "https://storage.googleapis.com/assignment01-453218.appspot.com/williams.png",
            },
        ]
        for team in sample_teams:
            firestore_db.collection("teams").add(team)

@app.on_event("startup")
async def startup_event():
    seed_sample_data()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
