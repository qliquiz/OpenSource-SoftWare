"""
License plate API router module.

This module defines FastAPI routes for managing license plate listings,
including CRUD operations, top ratings, likes, and price history.
"""

from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, and_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.crud.license_plate import (
    get_license_plate,
    get_license_plates_by_user,
    create_license_plate,
    get_top_plates,
    can_view_price_history,
    get_price_history,
    create_top_rating,
    create_price_history_entry,
    update_plate_with_price_history,
    check_plate_like,
    get_plate_likes_count,
    toggle_plate_like
)
from backend.app.crud.user import check_subscription_features, get_seller_statistics
from backend.app.database import get_db
from backend.app.dependencies import get_current_user_optional, get_current_user
from backend.app.models import PlateLike, User, LicensePlate
from backend.app.schemas import (
    FeatureType,
    LicensePlateCreate,
    LicensePlateUpdate,
    TopRatingCreate,
    LicensePlateOut
)

router = APIRouter()

# Create directories for storing images
TEMP_UPLOAD_DIR = Path('/tmp').resolve()
PLATES_PHOTOS_DIR = Path('/static/plates').resolve()

# Create directories if they don't exist
TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PLATES_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/top")
async def read_top_license_plates(
    limit: Optional[int] = Query(default=None),
    region_id: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve top-rated license plates.

    Args:
        limit: Maximum number of plates to return
        region_id: Filter by region ID
        db: Database session

    Returns:
        List of top-rated license plates
    """
    plates = await get_top_plates(db, limit=limit, region_id=region_id)
    return plates


@router.get("/{plate_id}")
async def read_license_plate(
    plate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Retrieve a specific license plate by ID.

    Args:
        plate_id: License plate ID
        db: Database session
        current_user: Optional current user for additional permissions

    Returns:
        License plate details, seller information, and price history if available
    
    Raises:
        HTTPException: If the license plate is not found
    """
    # Get the license plate
    plate = await get_license_plate(db, plate_id)
    if not plate:
        raise HTTPException(status_code=404, detail="Номерной знак не найден")

    # Increment view counter
    plate.views_count += 1
    db.add(plate)
    await db.flush()

    seller_info = await get_seller_statistics(db, plate.seller_id)
    price_history = None

    # Add price history if user has access
    if current_user and await can_view_price_history(db, current_user.id):
        price_history = await get_price_history(db, plate_id)

    return {
        "plate": plate,
        "seller": seller_info,
        "price_history": price_history if price_history is not None else []
    }


@router.get("")
async def read_license_plates(
    request: Request,
    skip: int = 0,
    limit: int = 10,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    region: Optional[int] = None,
    rating_min: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve license plates with filtering options.

    Args:
        request: FastAPI request object
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        price_min: Minimum price filter
        price_max: Maximum price filter
        region: Region ID filter
        rating_min: Minimum rating filter
        db: Database session

    Returns:
        Filtered license plates with total count
    """
    ip_address = request.client.host
    from backend.app.utils.geolocation import get_city_by_ip
    city = await get_city_by_ip(ip_address)

    # Create filters
    query_filters = []
    if price_min is not None:
        query_filters.append(LicensePlate.price >= price_min)
    if price_max is not None:
        query_filters.append(LicensePlate.price <= price_max)
    if region:
        query_filters.append(LicensePlate.region == region)
    if rating_min is not None:
        query_filters.append(LicensePlate.rating >= rating_min)

    # Query for filtering and counting total records
    total_query = await db.execute(select(func.count()).where(and_(*query_filters)))
    total_count = total_query.scalar()

    plates_query = await db.execute(
        select(LicensePlate)
        .offset(skip)
        .limit(limit)
        .options(
            selectinload(LicensePlate.region),
            selectinload(LicensePlate.city),
            selectinload(LicensePlate.seller)
        ).where(and_(*query_filters)),
    )

    plates = plates_query.scalars().all()
    content = jsonable_encoder({"data": plates, "total": total_count})

    return content


@router.get("/liked", response_model=List[LicensePlateOut])
async def get_liked_license_plates(
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve license plates liked by the current user.

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of license plates liked by the user
    """
    result = await db.execute(
        select(LicensePlate)
        .join(PlateLike, PlateLike.plate_id == LicensePlate.id)
        .where(PlateLike.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )

    liked_plates = result.scalars().all()
    return liked_plates


@router.get("/{plate_id}/price-history")
async def read_license_plate_price_history(
    plate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve price history for a specific license plate.

    Args:
        plate_id: License plate ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Price history for the license plate

    Raises:
        HTTPException: If user doesn't have required subscription or plate not found
    """
    # Check access rights
    if not await check_subscription_features(db, current_user.id, FeatureType.PRICE_HISTORY):
        raise HTTPException(
            status_code=403,
            detail="Просмотр истории цен доступен только пользователям с подписками Medium и Premium"
        )

    # Check if the plate exists
    plate = await get_license_plate(db, plate_id)
    if not plate:
        raise HTTPException(status_code=404, detail="Номерной знак не найден")

    history = await get_price_history(db, plate_id)
    return history


@router.get("/users/{user_id}")
async def read_license_plates_by_user(
    user_id: int,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve license plates belonging to a specific user.

    Args:
        user_id: User ID
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of license plates belonging to the user
    """
    plates = await get_license_plates_by_user(db, user_id, skip, limit)
    return plates


@router.post("")
async def create_new_license_plate(
    plate: LicensePlateCreate,
    pricing_type: str = Query(..., regex="^(free|paid|vip)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new license plate listing.

    Args:
        plate: License plate data
        pricing_type: Listing type (free, paid, or vip)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created license plate object

    Raises:
        HTTPException: If user doesn't have remaining free listings
    """
    # Check limits for free listings
    if pricing_type == "free":
        if current_user.remaining_free_listings <= 0:
            raise HTTPException(
                status_code=403,
                detail="У вас не осталось бесплатных объявлений в этом месяце"
            )

        # Decrease remaining free listings
        current_user.remaining_free_listings -= 1
        db.add(current_user)

    # Set listing validity period
    valid_days = {
        "free": 30,
        "paid": 30,
        "vip": 30
    }
    valid_until = datetime.utcnow() + timedelta(days=valid_days[pricing_type])

    # Create the listing
    new_plate = await create_license_plate(
        db,
        plate,
        current_user.id,
        pricing_type=pricing_type,
        valid_until=valid_until
    )

    # Create the first price history entry
    await create_price_history_entry(db, new_plate.id, plate.price)

    return new_plate


@router.put("/{plate_id}")
async def update_existing_license_plate(
    plate_id: int,
    plate_update: LicensePlateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing license plate listing.

    Args:
        plate_id: License plate ID
        plate_update: Updated license plate data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated license plate object

    Raises:
        HTTPException: If the plate doesn't exist or user doesn't have permission
    """
    existing_plate = await get_license_plate(db, plate_id)
    if not existing_plate:
        raise HTTPException(status_code=404, detail="Номерной знак не найден")

    if existing_plate.seller_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Вы не можете редактировать это объявление"
        )

    updated_plate = await update_plate_with_price_history(
        db,
        existing_plate,
        plate_update
    )
    return updated_plate


@router.post("/license-plates/{plate_id}/top-rating")
async def add_to_top_rating(
    plate_id: int,
    points: int = Query(..., ge=1, le=100),
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a license plate to top ratings.

    Args:
        plate_id: License plate ID
        points: Rating points (1-100)
        days: Validity period in days (1-365)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success status and message

    Raises:
        HTTPException: If the plate doesn't exist or user doesn't have permission
    """
    plate = await get_license_plate(db, plate_id)
    if not plate:
        raise HTTPException(status_code=404, detail="Номерной знак не найден")

    if plate.seller_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Вы можете добавлять в топ только свои номера"
        )

    rating = TopRatingCreate(
        plate_id=plate_id,
        points=points,
        valid_until=datetime.utcnow() + timedelta(days=days)
    )

    await create_top_rating(db, rating)
    return {"status": "success", "message": "Номер успешно добавлен в топ-рейтинг"}


@router.post("/{plate_id}/like")
async def toggle_like(
    plate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Toggle like status for a license plate.

    Args:
        plate_id: License plate ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated like status and total count

    Raises:
        HTTPException: If the plate doesn't exist or other errors occur
    """
    try:
        is_liked, total_likes = await toggle_plate_like(db, plate_id, current_user.id)

        return {
            "status": "success",
            "is_liked": is_liked,
            "total_likes": total_likes,
            "message": "Лайк поставлен" if is_liked else "Лайк убран"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{plate_id}/like")
async def get_like_status(
    plate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get like status for a license plate.

    Args:
        plate_id: License plate ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Like status and total count
    """
    is_liked = await check_plate_like(db, plate_id, current_user.id)
    total_likes = await get_plate_likes_count(db, plate_id)

    return {
        "is_liked": is_liked,
        "total_likes": total_likes
    }
