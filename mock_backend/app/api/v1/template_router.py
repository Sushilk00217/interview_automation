import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.sql.session import get_db_session
from app.db.sql.models.interview_template import InterviewTemplate
from app.schemas.interview import (
    InterviewTemplateCreate,
    InterviewTemplateUpdate,
    InterviewTemplateResponse
)

router = APIRouter(prefix="/api/v1/admin/templates", tags=["Admin Templates"])

@router.get("/", response_model=List[InterviewTemplateResponse])
async def list_templates(
    role: Optional[str] = Query(None),
    active_only: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    """List all templates with optional role and status filters."""
    stmt = select(InterviewTemplate)
    if role:
        stmt = stmt.where(InterviewTemplate.role_name == role)
    if active_only:
        stmt = stmt.where(InterviewTemplate.is_active == True)
    
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{template_id}", response_model=InterviewTemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a single template by ID."""
    template = await db.get(InterviewTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.post("/", response_model=InterviewTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: InterviewTemplateCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new interview template. Enforces single default per role."""
    new_template = InterviewTemplate(
        title=payload.title,
        role_name=payload.role_name,
        description=payload.description,
        is_rule_based=payload.is_rule_based,
        is_active=payload.is_active,
        is_default_for_role=payload.is_default_for_role,
        settings=payload.settings
    )
    
    db.add(new_template)
    await db.flush() # Get ID
    
    if payload.is_default_for_role and payload.role_name:
        # Enforce single default per role
        await db.execute(
            update(InterviewTemplate)
            .where(InterviewTemplate.role_name == payload.role_name)
            .where(InterviewTemplate.id != new_template.id)
            .values(is_default_for_role=False)
        )
    
    await db.commit()
    await db.refresh(new_template)
    return new_template

@router.put("/{template_id}", response_model=InterviewTemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    payload: InterviewTemplateUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a template. soft-delete use DELETE. Enforces single default per role."""
    template = await db.get(InterviewTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)
    
    if payload.is_default_for_role and template.role_name:
        # Enforce single default per role
        await db.execute(
            update(InterviewTemplate)
            .where(InterviewTemplate.role_name == template.role_name)
            .where(InterviewTemplate.id != template.id)
            .values(is_default_for_role=False)
        )
        
    await db.commit()
    await db.refresh(template)
    return template

@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Soft delete template by setting is_active=False."""
    template = await db.get(InterviewTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template.is_active = False
    await db.commit()
    return None

@router.patch("/{template_id}/activate", response_model=InterviewTemplateResponse)
async def toggle_template_activation(
    template_id: uuid.UUID,
    is_active: bool,
    db: AsyncSession = Depends(get_db_session)
):
    """Toggle is_active status."""
    template = await db.get(InterviewTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template.is_active = is_active
    await db.commit()
    await db.refresh(template)
    return template
