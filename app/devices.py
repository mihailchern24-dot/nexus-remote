from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Device, User
from app.schemas import DeviceCreate, DeviceResponse
from app.auth import get_current_user
router = APIRouter(prefix="/devices", tags=["devices"])
@router.post("", response_model=DeviceResponse)
async def create_device(device: DeviceCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Device).where(Device.peer_id == device.peer_id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Device with this peer_id already exists")
    db_device = Device(**device.model_dump(), user_id=current_user.id)
    db.add(db_device)
    await db.commit()
    await db.refresh(db_device)
    return db_device
@router.get("", response_model=list[DeviceResponse])
async def list_devices(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Device).where(Device.user_id == current_user.id))
    return result.scalars().all()
@router.delete("/{device_id}")
async def delete_device(device_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Device).where(Device.id == device_id).where(Device.user_id == current_user.id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    await db.delete(device)
    await db.commit()
    return {"message": "Device deleted"}
@router.patch("/{device_id}/status")
async def update_status(device_id: int, is_online: bool, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Device).where(Device.id == device_id).where(Device.user_id == current_user.id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.is_online = is_online
    device.last_seen = __import__("datetime").datetime.utcnow()
    await db.commit()
    return {"message": "Status updated"}
