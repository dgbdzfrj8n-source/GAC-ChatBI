"""
归因模板 v3 - 模板 CRUD 路由
端点：
  GET    /api/template-center/templates                  列表
  GET    /api/template-center/templates/{id}            详情
  POST   /api/template-center/templates                  创建
  PATCH  /api/template-center/templates/{id}            修改元信息
  POST   /api/template-center/templates/{id}/publish    发布新版本
  DELETE /api/template-center/templates/{id}            归档（软删）
  GET    /api/template-center/templates/{id}/versions   版本列表
"""
import os
import sys
from typing import Optional

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.auth import CurrentUser, get_current_user
from services.sop import (
    TemplateDB,
    TemplateCreateRequest,
    TemplateUpdateRequest,
    TemplatePublishVersionRequest,
    TemplateListResponse,
)
from config import get_settings

router = APIRouter(prefix="/api/template-center/templates", tags=["template-center"])


def _get_db() -> TemplateDB:
    settings = get_settings()
    return TemplateDB(settings.DATABASE_PATH)


@router.get("", response_model=TemplateListResponse)
def list_templates(
    category: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    db = _get_db()
    items = db.list_templates(category=category, keyword=keyword,
                              include_archived=include_archived,
                              limit=limit, offset=offset)
    # 简单总数
    total = len(db.list_templates(category=category, keyword=keyword,
                                  include_archived=include_archived, limit=10000, offset=0))
    return TemplateListResponse(items=items, total=total)


@router.get("/{template_id}")
def get_template(
    template_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    db = _get_db()
    tpl = db.get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    return tpl.model_dump(mode="json")


@router.post("", status_code=status.HTTP_201_CREATED)
def create_template(
    body: TemplateCreateRequest,
    user: CurrentUser = Depends(get_current_user),
):
    db = _get_db()
    # 检查 code 唯一性（包括已归档的，因为 DB UNIQUE 约束覆盖全部）
    settings = get_settings()
    con = duckdb.connect(settings.DATABASE_PATH, read_only=True)
    try:
        existing = con.execute(
            "SELECT 1 FROM attribution_template WHERE code = ? LIMIT 1", [body.code]
        ).fetchone()
    finally:
        con.close()
    if existing:
        raise HTTPException(status_code=409, detail=f"Template code already exists: {body.code}")
    tpl = db.create_template(
        name=body.name,
        code=body.code,
        description=body.description,
        category=body.category,
        tags=body.tags,
        steps=body.steps,
        created_by=user.username,
    )
    return tpl.model_dump(mode="json")


@router.patch("/{template_id}")
def update_template(
    template_id: str,
    body: TemplateUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
):
    db = _get_db()
    tpl = db.update_template(
        template_id=template_id,
        name=body.name,
        description=body.description,
        category=body.category,
        tags=body.tags,
        updated_by=user.username,
    )
    if not tpl:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    return tpl.model_dump(mode="json")


@router.post("/{template_id}/publish")
def publish_new_version(
    template_id: str,
    body: TemplatePublishVersionRequest,
    user: CurrentUser = Depends(get_current_user),
):
    db = _get_db()
    if not db.get_template(template_id):
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    try:
        new_version = db.publish_new_version(
            template_id=template_id,
            steps=body.steps,
            changelog=body.changelog,
            created_by=user.username,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"template_id": template_id, "new_version": new_version}


@router.delete("/{template_id}")
def archive_template(
    template_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    db = _get_db()
    if not db.archive_template(template_id):
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    return {"template_id": template_id, "archived": True}


@router.get("/{template_id}/versions")
def list_template_versions(
    template_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    db = _get_db()
    if not db.get_template(template_id):
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    versions = db.list_versions(template_id)
    return {"items": [v.model_dump(mode="json") for v in versions], "total": len(versions)}
