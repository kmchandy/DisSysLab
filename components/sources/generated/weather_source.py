import time
import requests
import json
from datetime import datetime

class WeatherSource:
    def __init__(self, city="Pasadena", poll_interval=3600, max_items=None):
        self.city = city
        self.poll_interval = poll_interval
        self.max_items = max_items
        self.items_yielded = 0

    def get_coordinates(self, city):
        # Use Open-Meteo geocoding API to get coordinates
        geocoding_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        response = requests.get(geocoding_url)
        response.raise_for_status()
        data = response.json()
        if data.get("results"):
            result = data["results"][0]
            return result["latitude"], result["longitude"], result["name"]
        else:
            raise Exception(f"City '{city}' not found")

    def get_weather(self, lat, lon):
        # Get current weather and forecast from Open-Meteo
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,weather_code&timezone=auto"
        response = requests.get(weather_url)
        response.raise_for_status()
        return response.json()

    def weather_code_to_description(self, code):
        codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow fall",
            73: "Moderate snow fall",
            75: "Heavy snow fall",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }
        return codes.get(code, f"Weather code {code}")

    def run(self):
        while True:
            if self.max_items and self.items_yielded >= self.max_items:
                break

            print("[Weather] Fetching...")
            try:
                lat, lon, city_name = self.get_coordinates(self.city)
                weather_data = self.get_weather(lat, lon)
                
                current = weather_data.get("current", {})
                daily = weather_data.get("daily", {})
                
                # Current weather
                temp = current.get("temperature_2m", "N/A")
                humidity = current.get("relative_humidity_2m", "N/A")
                wind_speed = current.get("wind_speed_10m", "N/A")
                weather_code = current.get("weather_code", 0)
                weather_desc = self.weather_code_to_description(weather_code)
                
                # Today's forecast
                if daily.get("temperature_2m_max") and daily.get("temperature_2m_min"):
                    temp_max = daily["temperature_2m_max"][0]
                    temp_min = daily["temperature_2m_min"][0]
                    forecast_text = f"High: {temp_max}°C, Low: {temp_min}°C"
                else:
                    forecast_text = ""
                
                text = f"Current: {temp}°C, {weather_desc}\n"
                text += f"Humidity: {humidity}%, Wind: {wind_speed} km/h\n"
                if forecast_text:
                    text += f"Today's forecast: {forecast_text}"
                
                yield {
                    "source": "weather",
                    "title": f"Weather in {city_name}",
                    "text": text,
                    "url": "",
                    "timestamp": datetime.now().isoformat(),
                }
                
                self.items_yielded += 1
                
            except Exception as e:
                print(f"[Weather] Error: {e}")
            
            if self.poll_interval:
                print(f"[Weather] Sleeping {self.poll_interval}s...")
                time.sleep(self.poll_interval)
            else:
                break

def weather(city="Pasadena", poll_interval=3600, max_items=None):
    return WeatherSource(city=city, poll_interval=poll_interval, max_items=max_items)