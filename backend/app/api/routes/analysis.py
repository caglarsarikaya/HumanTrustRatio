from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.routes.upload import get_result

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str) -> dict:
    result = get_result(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    profile_data = result.profile.model_dump() if result.profile else {}
    trust_data = result.trust_index.model_dump() if result.trust_index else {}
    footprints_data = [fp.model_dump() for fp in result.footprints]
    search_results_data = [sr.model_dump() for sr in result.search_results]

    return {
        "analysis_id": analysis_id,
        "resume_text": result.resume_text,
        "profile": profile_data,
        "search_queries": result.search_queries,
        "search_results": search_results_data,
        "footprints": footprints_data,
        "trust_index": trust_data,
    }
