#!/usr/bin/env python3
"""
Rain Monitoring Script

Purpose: This script monitors the probability of rain within the next three hours 
and sends email notifications when precipitation probability is 50% or greater.

Major Steps:
1. Fetch weather data from Open-Meteo API for Madison (default) or Boston
2. Analyze precipitation probability for the next 3 hours
3. If probability >= 50%, send email with precipitation details
4. Log all activities with timestamps to both console and log files
5. Apply retry logic with tenacity for robust API calls
"""

import os
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
import yagmail
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type


# Configuration
CITIES = {
    'madison': {
        'name': 'Madison',
        'url': "https://api.open-meteo.com/v1/forecast?latitude=43.0901&longitude=-89.4359&hourly=precipitation_probability,precipitation&timezone=America%2FChicago&forecast_days=1"
    },
    'boston': {
        'name': 'Boston', 
        'url': "https://api.open-meteo.com/v1/forecast?latitude=42.3745&longitude=-71.1178&hourly=precipitation_probability,precipitation&timezone=America%2FNew_York&forecast_days=1"
    }
}

DEFAULT_CITY = 'madison'
RAIN_THRESHOLD = 50  # Probability threshold in percentage
TESTING_MODE = False  # Set to True to send emails regardless of probability
EMAIL_SENDER = 'raychanan@gmail.com'
EMAIL_PASSWORD = 'aiyk zslp vpak bshl'
EMAIL_RECIPIENT = 'raychanan@gmail.com'


def setup_logging():
    """Setup logging to both console and file with timestamps."""
    # Create logs directory if it doesn't exist
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = logs_dir / f'rain_monitor_{timestamp}.log'
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Rain monitoring script started. Log file: {log_filename}")
    return logger


@retry(
    stop=stop_after_attempt(15),
    wait=wait_fixed(15),
    retry=retry_if_exception_type((requests.RequestException, Exception))
)
def fetch_weather_data(city='madison'):
    """
    Fetch weather data from Open-Meteo API with retry logic.
    
    Args:
        city (str): City name ('madison' or 'boston')
        
    Returns:
        dict: Weather data from API
        
    Raises:
        Exception: If API call fails after all retries
    """
    logger = logging.getLogger(__name__)
    
    if city not in CITIES:
        logger.warning(f"Unknown city '{city}', using default '{DEFAULT_CITY}'")
        city = DEFAULT_CITY
    
    url = CITIES[city]['url']
    city_name = CITIES[city]['name']
    
    logger.info(f"Fetching weather data for {city_name}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Validate response data
        if 'hourly' not in data:
            logger.warning("API response missing 'hourly' data")
            raise ValueError("Invalid API response format")
            
        if 'precipitation_probability' not in data['hourly']:
            logger.warning("API response missing precipitation probability data")
            raise ValueError("Missing precipitation probability data")
            
        logger.info(f"Successfully fetched weather data for {city_name}")
        return data
        
    except requests.exceptions.Timeout:
        logger.error("API request timed out")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise
    except ValueError as e:
        logger.error(f"Data validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching weather data: {e}")
        raise


def get_current_hour_index(data):
    """
    Find the index corresponding to the current hour in the API data.
    
    Args:
        data (dict): Weather data from API
        
    Returns:
        int: Index of current hour in the hourly data
    """
    logger = logging.getLogger(__name__)
    
    try:
        current_time = datetime.now()
        current_hour_str = current_time.strftime('%Y-%m-%dT%H:00')
        
        times = data['hourly']['time']
        
        # Find the closest matching hour
        for i, time_str in enumerate(times):
            if time_str.startswith(current_hour_str[:13]):  # Match up to hour
                logger.info(f"Found current hour index: {i} for time {time_str}")
                return i
                
        # If exact match not found, estimate based on current hour
        current_hour = current_time.hour
        logger.warning(f"Exact time match not found, estimating index based on hour {current_hour}")
        return current_hour
        
    except Exception as e:
        logger.error(f"Error finding current hour index: {e}")
        return 0  # Default to first hour if calculation fails


def analyze_rain_probability(data, city='madison'):
    """
    Analyze precipitation probability for the next 3 hours.
    
    Args:
        data (dict): Weather data from API
        city (str): City name for logging
        
    Returns:
        dict: Analysis results with rain probability and precipitation data
    """
    logger = logging.getLogger(__name__)
    
    try:
        current_index = get_current_hour_index(data)
        city_name = CITIES.get(city, {}).get('name', city)
        
        # Get data for next 3 hours
        times = data['hourly']['time']
        probabilities = data['hourly']['precipitation_probability']
        precipitations = data['hourly']['precipitation']
        
        analysis = {
            'city': city_name,
            'check_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'hours_data': [],
            'max_probability': 0,
            'total_precipitation': 0,
            'alert_triggered': False
        }
        
        # Analyze next 3 hours
        for i in range(3):
            hour_index = current_index + i
            
            if hour_index < len(times):
                time_str = times[hour_index]
                probability = probabilities[hour_index]
                precipitation = precipitations[hour_index]
                
                hour_data = {
                    'time': time_str,
                    'probability': probability,
                    'precipitation': precipitation
                }
                
                analysis['hours_data'].append(hour_data)
                analysis['max_probability'] = max(analysis['max_probability'], probability)
                analysis['total_precipitation'] += precipitation
                
                logger.info(f"Hour {i+1}: {time_str} - {probability}% chance, {precipitation}mm")
                
                if probability >= RAIN_THRESHOLD or TESTING_MODE:
                    analysis['alert_triggered'] = True
            else:
                logger.warning(f"Not enough forecast data for hour {i+1}")
        
        logger.info(f"Analysis complete - Max probability: {analysis['max_probability']}%, "
                   f"Total precipitation: {analysis['total_precipitation']}mm, "
                   f"Alert triggered: {analysis['alert_triggered']}")
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing rain probability: {e}")
        return None


@retry(
    stop=stop_after_attempt(15),
    wait=wait_fixed(15),
    retry=retry_if_exception_type(Exception)
)
def send_rain_alert_email(analysis):
    """
    Send email alert about rain probability with retry logic.
    
    Args:
        analysis (dict): Rain analysis results
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Preparing to send rain alert email")
        
        # Create email content
        if TESTING_MODE and analysis['max_probability'] < RAIN_THRESHOLD:
            subject = f"[TEST] Rain Monitor for {analysis['city']} - {analysis['max_probability']}% Probability"
            alert_reason = "This is a TEST EMAIL to verify email delivery is working."
        else:
            subject = f"Rain Alert for {analysis['city']} - {analysis['max_probability']}% Probability"
            alert_reason = f"This alert was triggered because rain probability is {RAIN_THRESHOLD}% or greater within the next 3 hours."
        
        content = f"""Rain {'Monitor Test' if TESTING_MODE and analysis['max_probability'] < RAIN_THRESHOLD else 'Alert'} - {analysis['city']}
Check Time: {analysis['check_time']}

RAIN PROBABILITY FORECAST (Next 3 Hours):
"""
        
        for i, hour_data in enumerate(analysis['hours_data']):
            hour_time = datetime.fromisoformat(hour_data['time'].replace('T', ' '))
            formatted_time = hour_time.strftime('%I:%M %p')
            content += f"Hour {i+1} ({formatted_time}): {hour_data['probability']}% chance, {hour_data['precipitation']}mm\n"
        
        content += f"""
SUMMARY:
- Maximum Probability: {analysis['max_probability']}%
- Total Expected Precipitation: {analysis['total_precipitation']}mm
- Alert Threshold: {RAIN_THRESHOLD}%
- Testing Mode: {'ON' if TESTING_MODE else 'OFF'}

{alert_reason}
"""
        
        # Send email
        yag = yagmail.SMTP(EMAIL_SENDER, EMAIL_PASSWORD)
        yag.send(EMAIL_RECIPIENT, subject, content)
        yag.close()
        
        logger.info(f"Rain alert email sent successfully to {EMAIL_RECIPIENT}")
        
    except Exception as e:
        logger.error(f"Failed to send rain alert email: {e}")
        raise


def main():
    """Main function to execute the rain monitoring process."""
    logger = setup_logging()
    
    try:
        logger.info("=== Rain Monitoring Check Started ===")
        
        # Fetch weather data
        weather_data = fetch_weather_data(DEFAULT_CITY)
        
        # Analyze rain probability
        analysis = analyze_rain_probability(weather_data, DEFAULT_CITY)
        
        if analysis is None:
            logger.error("Failed to analyze weather data")
            return
        
        # Send alert if needed
        if analysis['alert_triggered']:
            if TESTING_MODE and analysis['max_probability'] < RAIN_THRESHOLD:
                logger.info(f"TEST EMAIL triggered! Maximum probability: {analysis['max_probability']}% (below threshold but testing mode is ON)")
            else:
                logger.info(f"Rain alert triggered! Maximum probability: {analysis['max_probability']}%")
            send_rain_alert_email(analysis)
        else:
            logger.info(f"No alert needed. Maximum probability: {analysis['max_probability']}% (threshold: {RAIN_THRESHOLD}%)")
        
        logger.info("=== Rain Monitoring Check Completed ===")
        
    except Exception as e:
        logger.error(f"Rain monitoring check failed: {e}")
        raise


if __name__ == "__main__":
    main()