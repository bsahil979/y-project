import json
import os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "ticker_universe.json")


def load_universe():
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def all_symbols():
    data = load_universe()
    return [a["symbol"] for a in data["us"]] + [a["symbol"] for a in data["india"]]


def assets_flat():
    data = load_universe()
    out = []
    for region, key in (("US", "us"), ("India", "india")):
        for item in data[key]:
            out.append({
                "symbol": item["symbol"],
                "name": item["name"],
                "region": region,
                "category": f"{region} Equities",
            })
    return out
