"""Latest published Indian mutual fund NAV from AMFI."""
import datetime
import math
import re
import requests
from fastapi import APIRouter, HTTPException

router = APIRouter()


def parse_nav(text, code):
    for line in text.splitlines():
        columns = line.split(";")
        if len(columns) >= 6 and (columns[0].strip() == code or code in (columns[1].strip(), columns[2].strip())):
            nav = float(columns[-2])
            date = datetime.datetime.strptime(columns[-1].strip(), "%d-%b-%Y").date()
            if not math.isfinite(nav) or nav <= 0:
                raise ValueError("Invalid NAV")
            return {"scheme_code": columns[0].strip(), "name": " - ".join(c.strip() for c in columns[3:-2] if c.strip()), "nav": nav,
                    "date": date.isoformat(), "source": "AMFI"}
    raise LookupError("Scheme not in latest AMFI publication")


@router.get("/funds/{scheme_code}/nav")
def nav(scheme_code: str):
    if not re.fullmatch(r"(?:[0-9]{5,8}|IN[A-Z0-9]{10})", scheme_code):
        raise HTTPException(400, "Enter an AMFI scheme code or Indian fund ISIN.")
    try:
        response = requests.get("https://www.amfiindia.com/spages/NAVAll.txt", timeout=20)
        response.raise_for_status()
        return parse_nav(response.text, scheme_code)
    except LookupError:
        raise HTTPException(404, "Scheme not found in the latest AMFI NAV publication.")
    except (requests.RequestException, ValueError):
        raise HTTPException(502, "AMFI NAV unavailable. You can enter a dated NAV manually.")
