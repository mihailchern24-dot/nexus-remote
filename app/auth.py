import datetime
import random
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from app.database import get_db
from app.models import User, VerificationCode
from app.schemas import UserCreate, UserResponse, Token, VerifyEmail
from app.config import settings
router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user
async def send_verification_email(email: str, code: str):
    print(f"\n{'='*50}\nVERIFICATION CODE for {email}: {code}\n{'='*50}\n")
    if not settings.SMTP_HOST:
        return
    try:
        import aiosmtplib
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["From"] = settings.SMTP_FROM
        msg["To"] = email
        msg["Subject"] = "Nexus Remote — Verification Code"
        msg.set_content(f"Your code: {code}\n\nValid for 15 minutes.")
        await aiosmtplib.send(msg, hostname=settings.SMTP_HOST, port=settings.SMTP_PORT, username=settings.SMTP_USER, password=settings.SMTP_PASS, start_tls=True)
    except Exception as e:
        print(f"Email error: {e}")
@router.post("/register")
async def register(user_data: UserCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=user_data.email, password_hash=get_password_hash(user_data.password), is_verified=False)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    code = str(random.randint(100000, 999999))
    verif = VerificationCode(email=user_data.email, code=code, expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=15))
    db.add(verif)
    await db.commit()
    background_tasks.add_task(send_verification_email, user_data.email, code)
    return {"message": "User created. Check your email (or server console).", "user_id": user.id}
@router.post("/verify")
async def verify_email(data: VerifyEmail, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VerificationCode).where(VerificationCode.email == data.email).where(VerificationCode.code == data.code).where(VerificationCode.expires_at > datetime.datetime.utcnow()))
    verif = result.scalar_one_or_none()
    if not verif:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if user:
        user.is_verified = True
        await db.commit()
        return {"message": "Email verified successfully"}
    raise HTTPException(status_code=404, detail="User not found")
@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
@router.get("/me", response_model=UserResponse)
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user
