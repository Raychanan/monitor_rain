import time

import requests
import yagmail


# Function to fetch weather data
def fetch_weather_data():
    # boston
    url = "https://api.open-meteo.com/v1/forecast?latitude=42.3745&longitude=-71.1178&hourly=apparent_temperature,precipitation_probability&timezone=America%2FNew_York&past_days=1&forecast_days=1"
    # madison
    url = "https://api.open-meteo.com/v1/forecast?latitude=43.0901&longitude=-89.4359&hourly=apparent_temperature,precipitation_probability&timezone=America%2FChicago&past_days=1&forecast_days=1"

    response = requests.get(url)
    data = response.json()
    return data

# Function to extract temperature data for specific hours
def extract_temperatures(data, hours, start_index):
    temperatures = {}
    for hour in hours:
        index = start_index + hour
        time_str = data["hourly"]["time"][index]
        temperature = round(data["hourly"]["apparent_temperature"][index], 1)
        hour_only = time_str[-5:]  # Get the hour part from the time string
        temperatures[hour_only] = temperature
    return temperatures

# Function to compare temperatures between two sets of data
def compare_temperatures(today_temps, yesterday_temps):
    comparison = {}
    for hour in today_temps:
        today_temp = today_temps[hour]
        yesterday_temp = yesterday_temps.get(hour, 0)
        difference = round(today_temp - yesterday_temp, 1)
        sign = "+" if difference > 0 else ""
        comparison[hour] = {
            "today": today_temp,
            "yesterday": round(yesterday_temp, 1),
            "difference": f"{sign}{difference}"
        }
    return comparison

# Function to identify time periods with high precipitation probability
def identify_high_rain_probability(data, start_index):
    high_rain_times = []
    for i in range(24):
        time = data["hourly"]["time"][start_index + i]
        probability = data["hourly"]["precipitation_probability"][start_index + i]
        if probability > 49:
            high_rain_times.append((time, round(probability, 1)))
    return high_rain_times

# Function to send an email with the weather information
def send_email(today_temps, comparison, high_rain_times):
    # Use hardcoded credentials
    yag = yagmail.SMTP('raychanan@gmail.com', 'aiyk zslp vpak bshl') 

    comparison_text = "Comparison with yesterday's temperatures:\n"
    for hour, temps in comparison.items():
        comparison_text += f"{hour}: Today {temps['today']}°C, Yesterday {temps['yesterday']}°C, Difference: {temps['difference']}°C\n"

    rain_text = "Time periods with precipitation probability greater than 49% today:\n"
    if high_rain_times:
        for time, probability in high_rain_times:
            rain_text += f"{time}: {probability}%\n"
    else:
        rain_text += "None\n"

    contents = f"{comparison_text}\n{rain_text}"

    # Use hardcoded recipient
    yag.send('raychanan@gmail.com', 'Daily Weather Report', contents)

# Main function to execute the process
def main():
    data = fetch_weather_data()
    
    # "Yesterday" data is the first 24 hours (0-23)
    # "Today" data is the next 24 hours (24-47)
    hours = [8, 12, 15, 18]  # 8 AM, 12 PM, 3 PM, 6 PM in hourly data

    yesterday_temps = extract_temperatures(data, hours, start_index=0)
    today_temps = extract_temperatures(data, hours, start_index=24)
    
    comparison = compare_temperatures(today_temps, yesterday_temps)
    high_rain_times = identify_high_rain_probability(data, start_index=24)

    print(comparison, high_rain_times)
    send_email(today_temps, comparison, high_rain_times)

main()
# Schedule the main function to run every day at 7:00 AM
# schedule.every().day.at("08:00").do(main)

# Keep the script running to maintain the schedule
# while True:
#     schedule.run_pending()
#     time.sleep(1)
