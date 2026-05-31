"""
空间工具模块 —— Agent 调用 osmnx/geopandas 执行真实空间计算

依赖安装：pip install osmnx geopandas shapely geopy
"""

import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point, Polygon, box
from shapely.ops import nearest_points
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from typing import Optional
import json

geolocator = Nominatim(user_agent="spatial_agent")


def geocode(address: str) -> Optional[dict]:
    """地理编码：地址 → 经纬度"""
    try:
        loc = geolocator.geocode(address, timeout=10)
        if loc:
            return {"address": address, "lat": loc.latitude, "lon": loc.longitude}
    except Exception:
        pass
    return None


def reverse_geocode(lat: float, lon: float) -> Optional[dict]:
    """逆地理编码：经纬度 → 地址"""
    try:
        loc = geolocator.reverse((lat, lon), timeout=10)
        if loc:
            return {"lat": lat, "lon": lon, "address": loc.address}
    except Exception:
        pass
    return None


def search_pois(lat: float, lon: float, radius_m: int = 500, tags: Optional[dict] = None) -> dict:
    """
    在指定点周围搜索POI
    tags示例: {"amenity": "cafe"}, {"shop": "supermarket"}, {"leisure": "park"}
    """
    if tags is None:
        tags = {"amenity": True}

    try:
        gdf = ox.features_from_point(
            (lat, lon), dist=radius_m, tags=tags
        )
        if gdf.empty:
            return {"count": 0, "pois": [], "center": {"lat": lat, "lon": lon}, "radius_m": radius_m}

        pois = []
        for _, row in gdf.iterrows():
            center = row.geometry.centroid if hasattr(row.geometry, "centroid") else row.geometry
            name = row.get("name", "unnamed")
            if isinstance(name, list):
                name = name[0] if name else "unnamed"

            dist = geodesic((lat, lon), (center.y, center.x)).meters

            pois.append({
                "name": str(name),
                "type": str(tags.get(list(tags.keys())[0], "")),
                "lat": round(center.y, 6),
                "lon": round(center.x, 6),
                "distance_m": round(dist, 1),
            })

        pois.sort(key=lambda x: x["distance_m"])
        return {
            "count": len(pois),
            "pois": pois[:20],
            "center": {"lat": lat, "lon": lon},
            "radius_m": radius_m,
        }
    except Exception as e:
        return {"error": str(e), "count": 0, "pois": []}


def buffer_search(
    address: str, radius_m: int, poi_type: str
) -> dict:
    """
    缓冲搜索：在某地址周围 radius_m 米内搜索指定类型 POI
    先将地址地理编码 → 再调用 search_pois
    """
    loc = geocode(address)
    if not loc:
        return {"error": f"无法定位: {address}"}

    tag_map = {
        "咖啡店": {"amenity": "cafe"},
        "咖啡": {"amenity": "cafe"},
        "cafe": {"amenity": "cafe"},
        "餐厅": {"amenity": "restaurant"},
        "餐馆": {"amenity": "restaurant"},
        "restaurant": {"amenity": "restaurant"},
        "超市": {"shop": "supermarket"},
        "supermarket": {"shop": "supermarket"},
        "便利店": {"shop": "convenience"},
        "地铁站": {"station": "subway"},
        "公交站": {"highway": "bus_stop"},
        "加油站": {"amenity": "fuel"},
        "银行": {"amenity": "bank"},
        "atm": {"amenity": "atm"},
        "医院": {"amenity": "hospital"},
        "药房": {"amenity": "pharmacy"},
        "学校": {"amenity": "school"},
        "公园": {"leisure": "park"},
        "park": {"leisure": "park"},
        "停车场": {"amenity": "parking"},
        "停车场": {"amenity": "parking"},
        "酒店": {"tourism": "hotel"},
        "hotel": {"tourism": "hotel"},
        "健身房": {"leisure": "fitness_centre"},
        "gym": {"leisure": "fitness_centre"},
    }

    tags = tag_map.get(poi_type, {"amenity": poi_type})
    result = search_pois(loc["lat"], loc["lon"], radius_m, tags)
    result["query_address"] = address
    result["poi_type"] = poi_type

    for p in result.get("pois", []):
        p["type"] = poi_type

    return result


def nearest_poi(lat: float, lon: float, poi_type: str, k: int = 5) -> dict:
    """查找最近K个指定类型POI"""
    tag_map = {
        "咖啡店": {"amenity": "cafe"},
        "餐厅": {"amenity": "restaurant"},
        "地铁站": {"station": "subway"},
        "医院": {"amenity": "hospital"},
        "公园": {"leisure": "park"},
        "超市": {"shop": "supermarket"},
    }
    tags = tag_map.get(poi_type, {"amenity": poi_type})

    result = search_pois(lat, lon, radius_m=2000, tags=tags)
    result["pois"] = result["pois"][:k]
    result["count"] = len(result["pois"])
    result["query_type"] = poi_type
    return result


def calculate_route_info(
    start_lat: float, start_lon: float, end_lat: float, end_lon: float
) -> dict:
    """计算两点间的直线距离和方位"""
    start = (start_lat, start_lon)
    end = (end_lat, end_lon)
    distance_m = geodesic(start, end).meters

    if distance_m < 1000:
        dist_str = f"{distance_m:.0f} 米"
    else:
        dist_str = f"{distance_m / 1000:.1f} 公里"

    return {
        "start": {"lat": start_lat, "lon": start_lon},
        "end": {"lat": end_lat, "lon": end_lon},
        "distance_m": round(distance_m, 1),
        "distance_display": dist_str,
    }
