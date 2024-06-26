import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
import requests

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class LocationNotFoundException(Exception):
    pass


class JourneyNotFoundException(Exception):
    pass


@dataclass
class Location:
    name: str
    location_type: str
    latitude: str
    longitude: str
    has_local_service: str

    def __hash__(self) -> int:
        return hash((self.latitude, self.longitude))

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, self.__class__):
            return False

        return self.latitude == value.latitude and self.longitude == value.longitude


class VasttrafikAPI:
    ACCESS_TOKEN_FILE = "access_token.json"
    BASE_URL = "https://ext-api.vasttrafik.se/pr/v4"

    def __init__(self, authentication_key, data_root) -> None:
        self.data_root = data_root
        if not self._has_valid_token():
            self._generate_token(authentication_key)

        with open(
            os.path.join(self.data_root, self.ACCESS_TOKEN_FILE), "r", encoding="utf-8"
        ) as f:
            self.token = json.load(f)["access_token"]

        self.location_cache: dict[str:Location] = {}
        self.duration_cache: dict[(Location, Location):timedelta] = {}

    def _has_valid_token(self):
        valid = True
        if not os.path.exists(os.path.join(self.data_root, self.ACCESS_TOKEN_FILE)):
            valid = False

        else:
            with open(
                os.path.join(self.data_root, self.ACCESS_TOKEN_FILE),
                "r",
                encoding="utf-8",
            ) as f:
                token = json.load(f)
            decoded_token = jwt.decode(
                token["access_token"],
                options={"verify_signature": False},
            )
            expire_time = datetime.fromtimestamp(decoded_token["exp"])

            if expire_time < (datetime.now() + timedelta(minutes=10)):
                valid = False

        return valid

    def _generate_token(self, authentication_key):
        token_url = "https://ext-api.vasttrafik.se/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {authentication_key}",
        }
        data = "grant_type=client_credentials&scope=device_sgs"

        with open(
            os.path.join(self.data_root, self.ACCESS_TOKEN_FILE), "w", encoding="utf-8"
        ) as f:
            token = requests.post(
                token_url, data=data, headers=headers, timeout=10
            ).json()
            json.dump(token, f)

    def get_location(self, search) -> Location:
        if search in self.location_cache:
            location = self.location_cache[search]
            log.debug(
                "using cached location for %s",
                search,
            )
        else:
            url = f"{self.BASE_URL}/locations/by-text"
            headers = {
                "Authorization": f"Bearer {self.token}",
            }
            data = {"q": search, "limit": 1}
            response = requests.get(
                url, params=data, headers=headers, timeout=10
            ).json()

            if len(response["results"]) == 0:
                raise LocationNotFoundException

            result = response["results"][0]

            location = Location(
                name=result["name"],
                location_type=result["locationType"],
                latitude=result["latitude"],
                longitude=result["longitude"],
                has_local_service=result["hasLocalService"],
            )
            self.location_cache[search] = location

        return location

    def get_planned_duration(self, origin, destination):
        origin_location = self.get_location(origin)
        destination_location = self.get_location(destination)

        if (origin_location, destination_location) in self.duration_cache:
            duration = self.duration_cache[(origin_location, destination_location)]
            log.debug(
                "using cached duration from %(origin)s to %(destination)s",
                {"origin": origin, "destination": destination},
            )
        else:

            url = f"{self.BASE_URL}/journeys"
            headers = {
                "Authorization": f"Bearer {self.token}",
            }

            tomorrow = datetime.now() + timedelta(days=1)
            date = datetime(
                tomorrow.year,
                tomorrow.month,
                tomorrow.day,
                10,
                0,
                0,
                tzinfo=timezone.utc,
            ).isoformat()
            data = {
                "originName": origin_location.name,
                "originLatitude": origin_location.latitude,
                "originLongitude": origin_location.longitude,
                "destinationName": destination_location.name,
                "destinationLatitude": destination_location.latitude,
                "destinationLongitude": destination_location.longitude,
                "datetime": date,
                "dateTimeRelatesTo": "departure",
                "limit": 1,
            }
            response = requests.get(
                url, params=data, headers=headers, timeout=10
            ).json()

            if len(response["results"]) == 0:
                raise JourneyNotFoundException

            result = response["results"][0]
            if "departureAccessLink" in result:
                start_time = datetime.fromisoformat(
                    result["departureAccessLink"]["origin"]["plannedTime"]
                )
            elif "tripLegs" in result:
                start_time = datetime.fromisoformat(
                    result["tripLegs"][0]["origin"]["plannedTime"]
                )
            else:
                start_time = datetime.fromisoformat(
                    result["destinationLink"]["plannedDepartureTime"]
                )

            if "arrivalAccessLink" in result:
                end_time = datetime.fromisoformat(
                    result["arrivalAccessLink"]["destination"]["plannedTime"]
                )
            elif "tripLegs" in result:
                end_time = datetime.fromisoformat(
                    result["tripLegs"][-1]["destination"]["plannedTime"]
                )
            else:
                end_time = datetime.fromisoformat(
                    result["destinationLink"]["plannedArrivalTime"]
                )

            duration = end_time - start_time
            self.duration_cache[(origin_location, destination_location)] = duration

        return duration
