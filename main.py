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