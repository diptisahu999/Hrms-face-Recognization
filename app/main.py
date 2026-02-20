# app/main.py

import logging
import time
import numpy as np
import cv2
from fastapi import FastAPI, File, Form, UploadFile, Depends, HTTPException, Request, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from fastapi.staticfiles import StaticFiles
from . import crud, models, schemas
from .db import get_db, engine
from .cache import embedding_cache
from .config import settings
from .ai_processing import detect_and_recognize_faces, process_employee_images

# --- App Initialization ---
logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Face Recognition API")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Startup and Shutdown Events ---
@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    logging.info("Loading embeddings into cache on startup...")
    async for db in get_db():
        names, embeddings, ids ,member_code= await crud.load_all_embeddings(db)
        embedding_cache.update(names, embeddings, ids, member_code)
        break
    logging.info("Startup complete.")

# --- Helper for API Responses ---
def make_response(status, code, flag, message, data=None):
    return {
        "STATUS": status, "CODE": code, "FLAG": flag,
        "MESSAGE": message, "DATA": data
    }

# --- API Endpoints ---

@app.get("/face_scan", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/punch", response_class=HTMLResponse)
async def recognize_page(request: Request):
    return templates.TemplateResponse("recognize.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/root/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index_alternate.html", {"request": request})


@app.get("/scan", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("scan.html", {"request": request})

@app.get("/attendance", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("recognitions.html", {"request": request})

@app.get("/employee_upload/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/user/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("user.html", {"request": request})

# Scanner for Employees (accessible via Club-URL)
@app.get("/club/{club_code}/scan/", response_class=HTMLResponse)
async def club_scan_page(
    request: Request,
    club_code: str,
    db: AsyncSession = Depends(get_db)
):
    club = await crud.get_club_by_code(db, club_code)

    if not club:
        raise HTTPException(
            status_code=404,
            detail="Club doesnot exist"
        )

    return templates.TemplateResponse(
        "club_scan.html",
        {
            "request": request,
            "club_code": club_code,
            "club_name": club.club_name  # optional, nice for UI
        }
    )

@app.get("/hi")
def read_hi():
    return "TechV1z0r !"



####### employee all crud ############


@app.post("/upload", response_model=schemas.StandardResponse)
async def upload_images(
    name: str = Form(...),
    id: str = Form(...),
    member_code: str = Form(...),
    pictures: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    if not all([name, id, pictures]):
        raise HTTPException(status_code=400, detail="Missing required parameters.")

    try:
        files_data = []
        for file in pictures:
            contents = await file.read()
            files_data.append((file.filename, contents))

        avg_embedding, rep_img_path = await run_in_threadpool(
            process_employee_images, employee_name=name, employee_id=id, files_data=files_data
        )

        if avg_embedding is None:
            return JSONResponse(
                status_code=200,
                content=make_response(0, 2, False, "Failed to generate embeddings. No faces found or invalid images.")
            )

        existing_employee = await crud.get_employee_by_id(db, id)
        
        message = ""
        if existing_employee:
            await crud.update_employee(
                db, emp_id=id, name=name, member_code=member_code, 
                embedding=avg_embedding, image_path=rep_img_path
            )
            message = f"Employee {name} (ID: {id}) was successfully updated."
        else:
            await crud.create_employee(
                db, emp_id=id, name=name, member_code=member_code, 
                embedding=avg_embedding, image_path=rep_img_path
            )
            message = f"{name} is stored successfully."
        
        embedding_cache.update_or_add_employee(id, name, member_code, avg_embedding)
        
        return JSONResponse(
            status_code=200,
            content=make_response(1, 1, True, message)
        )

    except Exception as e:
        logging.error(f"Error during upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save images to database.")

recent_recognitions = {}
RECOGNITION_COOLDOWN = 60  # seconds


@app.delete("/employees/{employee_id}", response_model=schemas.StandardResponse)
async def delete_employee(employee_id: str, db: AsyncSession = Depends(get_db)):
    """
    Deletes an employee record from the database and the live cache.
    """
    deleted_employee = await crud.delete_employee_by_id(db, employee_id)

    if not deleted_employee:
        raise HTTPException(status_code=404, detail=f"Employee with ID '{employee_id}' not found.")

    embedding_cache.remove_employee(employee_id)

    message = f"Successfully deleted employee {deleted_employee.name} (ID: {employee_id})."
    return JSONResponse(
        status_code=200,
        content=make_response(1, 1, True, message)
    )

@app.get("/employees", response_model=schemas.EmployeeListResponse)
async def list_employees(db: AsyncSession = Depends(get_db)):
    """
    Returns a list of all registered employees with their ID, name, and member code.
    """
    # To fetch employees with image
    # employees_from_db = await crud.get_all_employees(db)
    
    # To fetch employees without image
    employees_from_db = await crud.get_all_employee(db)
    
    return {"employees": employees_from_db}


##########  employee recognisation ################

# Recognize using User's Scan-Tab
@app.post("/recognize", response_model=schemas.StandardResponse)
async def recognize(
    id: str = Form(...),
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db)
):
    try:
        # 1. Fetch employee by ID
        employee = await crud.get_employee_by_id(db, id)
        if not employee:
            return JSONResponse(
                status_code=200,
                content=make_response(0, 0, False, f"Employee with ID {id} not found.")
            )

        # 2. Convert stored embedding to numpy
        stored_emb = np.frombuffer(employee.embedding, dtype=np.float32)
        
        # 3. Read uploaded image
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image_bgr is None:
            return JSONResponse(
                status_code=200,
                content=make_response(0, 0, False, "Invalid image file.")
            )

        # 4. Prepare local cache for this specific employee
        # detect_and_recognize_faces expects (names, embeddings, ids, member_codes)
        local_cache = (
            [employee.name],
            np.array([stored_emb]),
            [employee.id],
            [employee.member_code]
        )

        # 5. Run detection and recognition
        recognized_faces = await run_in_threadpool(
            detect_and_recognize_faces, image_bgr=image_bgr, cache_data=local_cache
        )

        # 6. Check for match
        if recognized_faces:
            best_face = max(
                (f for f in recognized_faces if f.get("name") != "Unknown"), 
                key=lambda f: f.get("score", 0), 
                default=None
            )
            if best_face:
                # Capture values before commit potentially expires the object
                emp_name = employee.name
                emp_id = employee.id
                emp_member_code = employee.member_code

                # Log the recognition
                await crud.create_recognition_log(
                    db=db,
                    emp_id=emp_id,
                    name=emp_name,
                    member_code=emp_member_code
                )
                logging.info(f"✅ Recognition logged for {emp_name}")

                message = f"Match found: {emp_name}"
                return JSONResponse(
                    status_code=200,
                    content=make_response(1, 1, True, message, data={"name": emp_name, "score": best_face["score"]})
                )
        
        return JSONResponse(
            status_code=200,
            content=make_response(0, 0, False, "Face does not match the provided ID.")
        )

    except Exception as e:
        logging.exception("Error processing recognition request: %s", e)
        return JSONResponse(
            status_code=500,
            content=make_response(0, 0, False, "Internal server error during recognition.")
        )




##################################################
#######  recognize the face with club_id   #######


# Recognize using URL
@app.post("/recognize/{club_code}", response_model=schemas.RecognitionResponse)
async def recognize_by_url(
    club_code: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db)
):
    try:
        # ------------------ fetch club ------------------
        club = await crud.get_club_by_code(db, club_code)
        if not club:
            logging.warning(f"Invalid club_code received: {club_code}")
            return {"faces": []}

        club_id = club.id
        # ------------------------------------------------
        
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image_bgr is None:
            logging.error("cv2.imdecode failed, image is None.")
            return {"faces": []}

        cache_data = embedding_cache.get_all()
        if embedding_cache.is_empty():
            logging.warning("Recognition attempted but embedding cache is empty.")
            return {"faces": []}
            
        recognized_faces = await run_in_threadpool(
            detect_and_recognize_faces, image_bgr=image_bgr, cache_data=cache_data
        )

        if recognized_faces:
            best_face = max(
                (f for f in recognized_faces if f.get("name") != "Unknown"), 
                key=lambda f: f.get("score", 0), 
                default=None
            )
            if best_face:
                try:
                    names, _, ids, member_codes = embedding_cache.get_all()
                    idx = names.index(best_face["name"])
                    emp_id_to_log = ids[idx]
                    member_code_to_log = member_codes[idx]

                    # --- Cooldown logic: avoid multiple inserts for same person ---
                    now = time.time()
                    last_time = recent_recognitions.get(emp_id_to_log, 0)

                    if now - last_time > RECOGNITION_COOLDOWN:
                        # Update timestamp and insert record
                        recent_recognitions[emp_id_to_log] = now

                        await crud.create_recognition_log(
                            db=db,
                            emp_id=emp_id_to_log,
                            name=best_face["name"],
                            member_code=member_code_to_log,
                            club_id=club_id
                        )
                        logging.info(f"✅ Recognition logged for {best_face['name']}")
                    else:
                        logging.info(
                            f"⚠️ Skipped duplicate recognition for {best_face['name']} (within {RECOGNITION_COOLDOWN}s)"
                        )
                        
                except Exception as log_error:
                    logging.error(f"Failed to save recognition log: {log_error}")
        
        return {"faces": recognized_faces}
    except Exception as e:
        logging.exception("Error processing recognition request: %s", e)
        return {"faces": []}


##########  without club id face scan   ###########

# Recognize
@app.post("/recognizes", response_model=schemas.RecognitionResponse)
async def recognize(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db)
):
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image_bgr is None:
            logging.error("cv2.imdecode failed, image is None.")
            return {"faces": []}

        cache_data = embedding_cache.get_all()
        if embedding_cache.is_empty():
            logging.warning("Recognition attempted but embedding cache is empty.")
            return {"faces": []}
            
        recognized_faces = await run_in_threadpool(
            detect_and_recognize_faces, image_bgr=image_bgr, cache_data=cache_data
        )

        if recognized_faces:
            best_face = max(
                (f for f in recognized_faces if f.get("name") != "Unknown"), 
                key=lambda f: f.get("score", 0), 
                default=None
            )
            if best_face:
                try:
                    names, _, ids, member_codes = embedding_cache.get_all()
                    idx = names.index(best_face["name"])
                    emp_id_to_log = ids[idx]
                    member_code_to_log = member_codes[idx]

                    # --- Cooldown logic: avoid multiple inserts for same person ---
                    now = time.time()
                    last_time = recent_recognitions.get(emp_id_to_log, 0)

                    if now - last_time > RECOGNITION_COOLDOWN:
                        # Update timestamp and insert record
                        recent_recognitions[emp_id_to_log] = now

                        await crud.create_recognition_log(
                            db=db,
                            emp_id=emp_id_to_log,
                            name=best_face["name"],
                            member_code=member_code_to_log
                        )
                        logging.info(f"✅ Recognition logged for {best_face['name']}")
                    else:
                        logging.info(
                            f"⚠️ Skipped duplicate recognition for {best_face['name']} (within {RECOGNITION_COOLDOWN}s)"
                        )
                        
                except Exception as log_error:
                    logging.error(f"Failed to save recognition log: {log_error}")
        
        return {"faces": recognized_faces}
    except Exception as e:
        logging.exception("Error processing recognition request: %s", e)
        return {"faces": []}

###### Attendance log APIs ######

from fastapi import FastAPI, Request, Depends, HTTPException, Body
# ------------------------------------------------
# Route: POST API for date-wise recognition logs
# ------------------------------------------------
@app.post("/recognitions/datewise")
async def get_recognitions_datewise_post(
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch recognition logs grouped by date (POST method).
    Example body: {"date": "2025-10-30"}
    """
    try:
        date = data.get("date")
        name = data.get("name")
        club_id = data.get("club_id")

        grouped_data = await crud.get_recognitions_grouped_by_date(db)

        # Filter by specific date if provided
        if date:
            grouped_data = {date: grouped_data.get(date, [])}
        
        
        # Filter by Club
        if club_id:
            club_id = int(club_id)

            filtered_by_club = {}
            for d, logs in grouped_data.items():
                matched = [
                    log for log in logs
                    if log.get("club_id") == club_id
                ]
                if matched:
                    filtered_by_club[d] = matched

            grouped_data = filtered_by_club
    

        # If a name filter is provided, filter logs (case-insensitive substring match)
        if name:
            name_lower = name.lower()
            filtered = {}
            for d, logs in grouped_data.items():
                matched = [log for log in logs if name_lower in (log.get("name") or "").lower()]
                if matched:
                    filtered[d] = matched
            grouped_data = filtered

        return JSONResponse(
            status_code=200,
            content={
                "status": True,
                "message": "Recognition logs fetched successfully.",
                "data": grouped_data
            }
        )
    except Exception as e:
        logging.error(f"Error fetching recognitions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch recognition logs.")


# -------------------------------
# Simple in-memory session
# logged_in_users = set()


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login_action(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    # Use crud function
    user = await crud.get_user_by_username(db, username)

    if not user or user.password != password:  # TODO: replace with hash check later
        return JSONResponse({"FLAG": False, "MESSAGE": "Invalid credentials"}, status_code=401,)

    # Save logged-in user in session
    # logged_in_users.add(username)

    # redirect_url = "/admin" if user.is_admin else "/"
    if user.is_admin:
        redirect_url = "/admin"
    elif user.assigned_to is not None:
        redirect_url = "/user"
    else:
        redirect_url = "/home"

    response = JSONResponse(
        {
            "FLAG": True,
            "MESSAGE": f"Login successful!",
            "redirect": redirect_url,
        }
    )
    
    # Set cookie to track the logged-in user
    # response.set_cookie(key="username", value=username, httponly=True)
    response.set_cookie(key="user_id", value=str(user.id), httponly=True, samesite="lax",)
    response.set_cookie(key="club_id", value=str(user.assigned_to), httponly=False, samesite="lax",)
    response.set_cookie(key="is_admin", value=str(user.is_admin), httponly=True, samesite="lax",)
    return response

@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def signup_action(
    username: str = Form(...),
    name: str = Form(...),
    password: str = Form(...),
    mobile: str = Form(...),
    is_admin: bool = Form(False),
    assigned_club: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    # Username uniqueness
    existing_user = await crud.get_user_by_username(db, username)
    if existing_user:
        return JSONResponse({"FLAG": False, "MESSAGE": "Username already exists."})
    assigned_club_id = int(assigned_club) if assigned_club else None
    # Create user
    await crud.create_user(
        db=db,
        username=username,
        name=name,
        password=password,
        mobile=mobile,
        is_admin=is_admin,
        assigned_to = assigned_club_id
    )

    return JSONResponse({
        "FLAG": True,
        "MESSAGE": "Account created successfully!",
        "redirect": "/admin"   # ✅ REQUIRED CHANGE
    })

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: AsyncSession = Depends(get_db)):
    # Get the username from the cookie
    # username = request.cookies.get("username")
    is_admin = request.cookies.get("is_admin")
    if is_admin != "True":
        return RedirectResponse("/login")

    club_id = request.cookies.get("club_id")

    # No cookie or not logged in → redirect to login
    # if not username or username not in logged_in_users:
    #     return RedirectResponse("/login")

    # Fetch the user from DB
    # user = await crud.get_user_by_username(db, username)
    
    # Not found or not admin → redirect to login
    # if not user or not user.is_admin:
    #     return RedirectResponse("/login")

    # Admin verified → render page
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "club_id": club_id 
        }
    )


@app.get("/logout")
async def logout(request: Request):
    # response = RedirectResponse("/")
    response = RedirectResponse("/root/")
    response.delete_cookie("user_id")
    response.delete_cookie("club_id")
    response.delete_cookie("is_admin")
    return response


# -------------------------------
# Club APIs
# -------------------------------

# Get all clubs
@app.get("/clubs", response_model=schemas.ClubListResponse)
async def list_clubs(db: AsyncSession = Depends(get_db)):
    clubs = await crud.get_all_clubs(db)
    return {"clubs": clubs}

@app.post("/clubs", response_model=schemas.StandardResponse)
async def add_club(payload: schemas.ClubCreateRequest, db: AsyncSession = Depends(get_db)):
    if len(payload.club_code) != 18:
        return JSONResponse(
            content=make_response(0, 0, False, "Club code must be 18 digits")
        )

    existing = await crud.get_club_by_code(db, payload.club_code)
    if existing:
        return JSONResponse(
            content=make_response(0, 0, False, "Club code must be unique")
        )

    # dynamically generate URL using club_code
    club_url = f"/club/{payload.club_code}/scan/"


    club = await crud.create_club(
        db,
        club_code=payload.club_code,
        club_name=payload.club_name,
        url=club_url
    )

    club_info = schemas.ClubInfo.from_orm(club)

    return JSONResponse(
        content=make_response(
            1, 1, True,
            "Club created successfully",
            data={"club": club_info.model_dump()}  # ✅ PURE DICT
        )
    )

@app.put("/clubs/{club_id}", response_model=schemas.StandardResponse)
async def update_club_endpoint(club_id: int, payload: schemas.ClubUpdateRequest, db: AsyncSession = Depends(get_db)):
    if len(payload.club_code) != 18:
        return JSONResponse(
            content=make_response(0, 0, False, "Club code must be 18 digits")
        )
    existing = await crud.get_club_by_code(db, payload.club_code) 
    if existing and existing.id != club_id:
        return JSONResponse(
            content=make_response(0, 0, False, "Club code must be unique")
        )
        
    # dynamically generate URL using club_code
    club_url = f"/club/{payload.club_code}/scan/"
    
    club = await crud.update_club(db, club_id, club_code=payload.club_code, club_name=payload.club_name, url=club_url)
    if not club:
        return JSONResponse(
            content=make_response(0, 0, False, "Club not found")
        )
    club_info = schemas.ClubInfo.from_orm(club)

    return JSONResponse(
        content=make_response(
            1, 1, True,
            "Club updated successfully",
            data={"club": club_info.model_dump()}
        )
    )


# Delete a club
@app.delete("/clubs/{club_id}", response_model=schemas.StandardResponse)
async def delete_club_endpoint(club_id: int, db: AsyncSession = Depends(get_db)):
    success = await crud.delete_club(db, club_id)
    if not success:
        return JSONResponse(
            content=make_response(0, 0, False, "Club not found")
        )
    return JSONResponse(
        content=make_response(1, 1, True, "Club deleted successfully")
    )

@app.get("/api/clubs/list")
async def list_clubs_for_signup(db: AsyncSession = Depends(get_db)):
    clubs = await crud.get_all_clubs(db)
    return {
        "clubs": [
            {"id": c.id, "club_name": c.club_name}
            for c in clubs
        ]
    }





# -------------------------------
# USER APIs
# -------------------------------

@app.get("/clubs/{club_id}/users")
async def get_users_for_club(club_id: int, db: AsyncSession = Depends(get_db)):
    users = await crud.get_users_by_club(db, club_id)

    return {
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "username": u.username,
                "password": u.password,
                "mobile": u.mobile,
            }
            for u in users
        ]
    }


@app.put("/users/{user_id}")
async def update_user_endpoint(
    user_id: int,
    payload: schemas.UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    # Username uniqueness check
    existing = await crud.get_user_by_username(db, payload.username)
    if existing and existing.id != user_id:
        return JSONResponse({
            "FLAG": False,
            "MESSAGE": "Username already exists."
        })

    user = await crud.update_user(
        db,
        user_id=user_id,
        name=payload.name,
        username=payload.username,
        password=payload.password,
        mobile=payload.mobile
    )

    if not user:
        return JSONResponse({
            "FLAG": False,
            "MESSAGE": "User not found."
        })

    return JSONResponse({
        "FLAG": True,
        "MESSAGE": "User updated successfully."
    })


@app.delete("/users/{user_id}")
async def delete_user_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    success = await crud.delete_user(db, user_id)

    if not success:
        return JSONResponse({
            "FLAG": False,
            "MESSAGE": "User not found."
        })

    return JSONResponse({
        "FLAG": True,
        "MESSAGE": "User deleted successfully."
    })
