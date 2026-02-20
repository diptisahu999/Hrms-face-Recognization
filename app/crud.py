# app/crud.py

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Tuple, Optional

from . import models, schemas


# --------------------- EMPLOYEES --------------------

async def get_employee_by_id(db: AsyncSession, emp_id: str) -> Optional[models.Employee]:
    """Fetch a single employee by their ID."""
    result = await db.execute(select(models.Employee).filter(models.Employee.id == emp_id))
    return result.scalars().first()

async def create_employee(
    db: AsyncSession, 
    emp_id: str, 
    name: str, 
    member_code: str, 
    embedding: np.ndarray, 
    image_path: str
):
    """Create a new employee record in the database."""
    db_employee = models.Employee(
        id=emp_id,
        name=name,
        member_code=member_code, # And also here
        embedding=embedding.tobytes(),
        image_path=image_path
    )
    db.add(db_employee)
    await db.commit()
    await db.refresh(db_employee)
    return db_employee

async def update_employee(
    db: AsyncSession,
    emp_id: str,
    name: str,
    member_code: Optional[str],
    embedding: np.ndarray,
    image_path: str
):
    """Fetches an employee by ID and updates their details."""
    db_employee = await get_employee_by_id(db, emp_id)
    if db_employee:
        db_employee.name = name
        db_employee.member_code = member_code
        db_employee.embedding = embedding.tobytes()
        db_employee.image_path = image_path
        await db.commit()
        await db.refresh(db_employee)
    return db_employee

async def delete_employee_by_id(db: AsyncSession, emp_id: str) -> Optional[models.Employee]:
    """Deletes an employee from the database by their ID."""
    db_employee = await get_employee_by_id(db, emp_id)
    if db_employee:
        await db.delete(db_employee)
        await db.commit()
    return db_employee

async def load_all_embeddings(db: AsyncSession) -> Tuple[List[str], np.ndarray, List[str], List[str]]:
    """Load all employee names, IDs, and embeddings from the database."""
    result = await db.execute(select(
        models.Employee.name, 
        models.Employee.embedding, 
        models.Employee.id, 
        models.Employee.member_code
    ))
    
    names, embeddings, ids, member_codes = [], [], [], []
    for name, emb_bytes, emp_id, member_code in result.all():
        if len(emb_bytes) % 4 == 0:
            emb = np.frombuffer(emb_bytes, dtype=np.float32)
            if emb.shape[0] == 512:
                embeddings.append(emb)
                names.append(name)
                ids.append(emp_id)
                member_codes.append(member_code)

    return names, np.array(embeddings), ids, member_codes

# Fetch list of whole Employee model
async def get_all_employees(db: AsyncSession) -> List[models.Employee]:
    """Fetches all employee records from the database."""
    result = await db.execute(select(models.Employee))
    return result.scalars().all()


# Fetch employees without Image
async def get_all_employee(db: AsyncSession):
    result = await db.execute(
        select(
            models.Employee.id,
            models.Employee.name,
            models.Employee.member_code,
        )
    )
    return result.all()



# --------------------- RECOGNITION LOG --------------------------


async def create_recognition_log(
    db: AsyncSession, 
    emp_id: str, 
    name: str, 
    member_code: str,
    club_id: Optional[int] = None
):
    """Creates a new entry in the recognition_log table."""
    db_log = models.RecognitionLog(
        employee_id=emp_id,
        name=name,
        member_code=member_code,
        club_id=club_id
    )
    db.add(db_log)
    await db.commit()
    return db_log



# --------------------------- USER ----------------------------

# Get user by ID
async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(models.User).where(models.User.id == user_id)
    )
    return result.scalar_one_or_none()


# --- Fetch a user by username ---
async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(models.User).where(models.User.username == username))
    return result.scalar_one_or_none()


# Get users by club
async def get_users_by_club(db: AsyncSession, club_id: int):
    result = await db.execute(
        select(models.User).where(models.User.assigned_to == club_id)
    )
    return result.scalars().all()


# --- Create a new User ---
async def create_user(db: AsyncSession, username: str, name:str, password: str, mobile:str, is_admin: bool = False, assigned_to: str = None):
    """Creates a new user in the database."""
    db_user = models.User(username=username, name=name, password=password, mobile=mobile, is_admin=is_admin, assigned_to=assigned_to)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user
   
   
# Update user
async def update_user(
    db: AsyncSession,
    user_id: int,
    name: str,
    username: str,
    password: str,
    mobile: str
):
    user = await get_user_by_id(db, user_id)
    if not user:
        return None

    user.name = name
    user.username = username
    user.password = password
    user.mobile = mobile

    await db.commit()
    await db.refresh(user)
    return user
    
    
# Delete user
async def delete_user(db: AsyncSession, user_id: int):
    user = await get_user_by_id(db, user_id)
    if not user:
        return False

    await db.delete(user)
    await db.commit()
    return True



    
########### Attendance log #############

# ------------------------------------------------
# ✅ Updated Function: Remove duplicate names per date
# ------------------------------------------------
from sqlalchemy import select
from collections import defaultdict

async def get_recognitions_grouped_by_date(db: AsyncSession):
    from datetime import timedelta
    
    result = await db.execute(
        select(
            models.RecognitionLog.employee_id,
            models.RecognitionLog.name,
            models.RecognitionLog.member_code,
            models.RecognitionLog.recognized_at,
            models.RecognitionLog.club_id
        ).order_by(models.RecognitionLog.recognized_at.desc())
    )
    rows = result.fetchall()

    grouped = defaultdict(list)
    # Track last scan time per employee per date to avoid duplicates within 1 minute
    last_scan_time = {}

    for employee_id, name, member_code, recognized_at, club_id in rows:
        if not recognized_at:
            continue

        date_str = recognized_at.strftime("%Y-%m-%d")
        time_str = recognized_at.strftime("%H:%M:%S")

        # ✅ Create a unique key for employee+date
        emp_date_key = f"{employee_id}_{date_str}"
        
        # Check if same employee was scanned within last 1 minute on same date
        if emp_date_key in last_scan_time:
            time_diff = last_scan_time[emp_date_key] - recognized_at
            # If scanned within 1 minute (60 seconds), skip this duplicate entry
            if time_diff.total_seconds() < 10:
                continue
        
        # Update last scan time for this employee on this date
        last_scan_time[emp_date_key] = recognized_at
        
        grouped[date_str].append({
            "employee_id": employee_id,
            "name": name,
            "member_code": member_code,
            "time": time_str,
            "club_id": club_id
        })

    # ✅ Sort by date (latest first)
    return dict(sorted(grouped.items(), reverse=True))



# ---------------------- CLUB -----------------------

async def get_all_clubs(db: AsyncSession) -> List[models.Club]:
    result = await db.execute(select(models.Club).order_by(models.Club.id))
    return result.scalars().all()

# Fetch single club by id
async def get_club_by_id(db: AsyncSession, club_id: int) -> Optional[models.Club]:
    result = await db.execute(select(models.Club).where(models.Club.id == club_id))
    return result.scalars().first()

# Fetch single club by club_code
async def get_club_by_code(db: AsyncSession, club_code: str) -> Optional[models.Club]:
    result = await db.execute(select(models.Club).where(models.Club.club_code == club_code))
    return result.scalars().first()

# Create a new club
async def create_club(db: AsyncSession, club_code: str, club_name: str, url: str) -> models.Club:
    db_club = models.Club(club_code=club_code, club_name=club_name, url=url)
    db.add(db_club)
    await db.commit()
    await db.refresh(db_club)
    return db_club

# Update club
async def update_club(db: AsyncSession, club_id: int, club_code: str, club_name: str, url: str) -> Optional[models.Club]:
    db_club = await get_club_by_id(db, club_id)
    if db_club:
        db_club.club_code = club_code  
        db_club.club_name = club_name
        db_club.url = url
        await db.commit()
        await db.refresh(db_club)
    return db_club

# Delete club
async def delete_club(db: AsyncSession, club_id: int) -> bool:
    db_club = await get_club_by_id(db, club_id)
    if db_club:
        await db.delete(db_club)
        await db.commit()
        return True
    return False


