from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import require_admin
from app.models import SuperstoreSale, User
from app.schemas import SaleCreate, SaleRead, SaleUpdate

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: SaleCreate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
) -> SuperstoreSale:
    """Create a new sale order. Admin only."""
    sale = SuperstoreSale(**payload.model_dump())
    session.add(sale)
    await session.commit()
    await session.refresh(sale)
    return sale


@router.put("/{order_id}", response_model=SaleRead)
async def update_order(
    order_id: int,
    payload: SaleUpdate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
) -> SuperstoreSale:
    """Update an existing sale order (partial update). Admin only."""
    sale = await session.get(SuperstoreSale, order_id)
    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Apply only the fields that were explicitly set in the request body
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sale, field, value)

    await session.commit()
    await session.refresh(sale)
    return sale


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
) -> None:
    """Delete a sale order. Admin only."""
    sale = await session.get(SuperstoreSale, order_id)
    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    await session.delete(sale)
    await session.commit()
