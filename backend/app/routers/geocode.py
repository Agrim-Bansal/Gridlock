"""Cell name reverse-lookup endpoint."""

from fastapi import APIRouter, Query

from app.schemas import CellLocationOut, CellNamesResponse
from app.services import geocode_lookup

router = APIRouter()


@router.get("/cell-names", response_model=CellNamesResponse)
def get_cell_names(cell_ids: str | None = Query(None)):
    if cell_ids:
        ids = [cid.strip() for cid in cell_ids.split(",") if cid.strip()]
        locations = geocode_lookup.resolve_bulk(ids)
    else:
        locations = geocode_lookup.all_locations()

    return CellNamesResponse(
        cell_names={
            cid: CellLocationOut(
                road=loc.road,
                locality=loc.locality,
                display_name=loc.display_name,
            )
            for cid, loc in locations.items()
        }
    )
