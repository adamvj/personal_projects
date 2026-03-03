#!/usr/bin/env python3
import requests
import sys

# --- Configuration ---
# Generate a unique topic name for ntfy.sh (replace with something secret if you want to avoid spam, but keep it simple for now)
# The user will need to subscribe to this topic on their phone's ntfy app.
NTFY_TOPIC = "YOUR_SECRET_NTFY_TOPIC_HERE" # CHANGE THIS TO YOUR OWN SECRET TOPIC
# Determine the thresholds for "high" pollen count (grains/m3)
# Adjusted to be more sensitive (lower thresholds)
POLLEN_THRESHOLDS = {
    "alder_pollen": 45.0,   # Tree Pollen (grains/m³)
    "birch_pollen": 45.0,   # Tree Pollen (grains/m³)
    "grass_pollen": 10.0,   # Grass Pollen (grains/m³)
    "mugwort_pollen": 25.0, # Weed Pollen (grains/m³)
    "olive_pollen": 45.0,   # Tree Pollen (grains/m³)
    "ragweed_pollen": 25.0, # Weed Pollen (grains/m³)
    "pm10": 45.0,           # Particulate Matter 10 (μg/m³) - WHO guidelines
    "pm2_5": 15.0,          # Particulate Matter 2.5 (μg/m³) - WHO guidelines
    "us_aqi": 50.0          # US Air Quality Index - >50 is "Moderate" risk for sensitive groups
}

def get_location():
    try:
        response = requests.get("http://ip-api.com/json/")
        response.raise_for_status()
        data = response.json()
        if data["status"] == "success":
            return data["lat"], data["lon"], data.get("city", "your location")
        else:
            print(f"Error getting location: {data.get('message')}")
            return None, None, None
    except requests.RequestException as e:
        print(f"Failed to fetch location: {e}")
        return None, None, None

def get_pollen_data(lat, lon):
    """Fetch daily maximum pollen data from Open-Meteo for the given coordinates."""
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen,pm10,pm2_5,us_aqi",
        "timezone": "auto",
        "forecast_days": 1 # We only care about today
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Failed to fetch pollen data: {e}")
        return None

def check_pollen_levels_and_notify(data, city):
    """Check if any pollen levels exceed their specific thresholds and send a notification."""
    if not data or "hourly" not in data:
        print("Invalid data received from API.")
        return

    hourly_data = data["hourly"]
    high_metrics = {}
    
    # Check each metric against its specific threshold
    for pt, threshold in POLLEN_THRESHOLDS.items():
        if pt in hourly_data and len(hourly_data[pt]) > 0:
            # Filter out None values and find the daily maximum
            valid_counts = [val for val in hourly_data[pt] if val is not None]
            if valid_counts:
                max_count = max(valid_counts)
                if max_count >= threshold:
                    # Format name: "grass_pollen" -> "Grass", "pm2_5" -> "Pm2 5", etc
                    name = pt.replace("_pollen", "").replace("_", ".").upper() if "pm" in pt or "aqi" in pt else pt.replace("_pollen", "").capitalize()
                    high_metrics[name] = max_count

    if high_metrics:
        # Construct message
        message = f"Poor air quality or pollen detected in {city} today!\n"
        for name, count in high_metrics.items():
            unit = "AQI" if "AQI" in name else "μg/m³" if "PM" in name else "grains/m³"
            message += f"• {name}: {count:.1f} {unit}\n"
        message += "Consider staying inside or taking precautions!"
        
        print("High allergens/pollutants detected! Sending alert notification...")
        send_ntfy_notification(message, title="(=_=) Air Quality Alert", tags="warning,mask")
    else:
        message = f"Air quality and pollen in {city} are currently in good ranges. It is safe to go outside!"
        print("All clear! Sending safe notification...")
        send_ntfy_notification(message, title="(^_^) All Clear!", tags="white_check_mark,sun_with_face")

def send_ntfy_notification(message, title="Pollen Update", tags="bell"):
    """Send a push notification via ntfy.sh."""
    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    try:
        response = requests.post(url, 
                                 data=message.encode('utf-8'),
                                 headers={"Title": title, "Tags": tags})
        response.raise_for_status()
        print("Notification sent successfully.")
    except requests.RequestException as e:
        print(f"Failed to send notification: {e}")

if __name__ == "__main__":
    print("Checking Pollen Levels...")
    lat, lon, city = get_location()
    
    if lat and lon:
        print(f"Location detected: {city} ({lat}, {lon})")
        pollen_data = get_pollen_data(lat, lon)
        check_pollen_levels_and_notify(pollen_data, city)
    else:
        print("Could not proceed without location.")
        sys.exit(1)
