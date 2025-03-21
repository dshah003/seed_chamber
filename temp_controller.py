import os
import glob
import time
import RPi.GPIO as GPIO
import logging
from logging.handlers import RotatingFileHandler


# GPIO Pin Configuration
MOSFET_PIN = 18  # BCM Pin controlling the MOSFET
TEMP_SENSOR_PATH = "/sys/bus/w1/devices/"  # DS18B20 sensor directory

# Temperature Thresholds
LOWER_THRESHOLD = 25.0  # Turn ON heater below this
UPPER_THRESHOLD = 27.0  # Turn OFF heater above this
DUTY_CYCLE = 50  # 30% PWM Duty Cycle

# Setup log rotation (Max 10 MB per file, keep last 10 logs)
log_handler = RotatingFileHandler(
	"heater_control.log", maxBytes=10*1024*1024, backupCount=10
)

# Configure Logger
log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)


logger.info("Program Initiating")


# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(MOSFET_PIN, GPIO.OUT)
pwm = GPIO.PWM(MOSFET_PIN, 1000)  # 1 kHz frequency
pwm.start(0)  # Initially off

# Enable 1-Wire Interface (Required for DS18B20)
os.system("modprobe w1-gpio")
os.system("modprobe w1-therm")

# Locate DS18B20 Sensor
def find_sensor():
	device_folders = glob.glob(TEMP_SENSOR_PATH + "28*")
	if device_folders:
		logger.info("Temperature Sensor found. ")
		return device_folders[0] + "/w1_slave"
	else:
		logger.error("Temperature Sensor not found")
		raise Exception("No DS18B20 sensor found!")

SENSOR_FILE = find_sensor()

# Function to Read Temperature
def read_temperature():
	with open(SENSOR_FILE, "r") as f:
		lines = f.readlines()
	while "YES" not in lines[0]:  # Ensure data is valid
		time.sleep(0.2)
		with open(SENSOR_FILE, "r") as f:
			lines = f.readlines()
	temp_str = lines[1].split("t=")[-1]
	temperature = float(temp_str) / 1000.0  # Convert to °C
	return temperature

# Control Heater Based on Temperature
try:
	heater_on = False
	while True:
		temp = read_temperature()
		print(f"Current Temperature: {temp:.2f}C")
		logger.info(f"Current Temperature: {temp:.2f}C")

		if temp < LOWER_THRESHOLD and not heater_on:
			print("Turning Heater ON")
			logger.info(f"Turning Heater ON at {DUTY_CYCLE}% Duty Cycle")
			pwm.ChangeDutyCycle(DUTY_CYCLE)
			heater_on = True
		elif temp > UPPER_THRESHOLD and heater_on:
			print("Turning Heater OFF")
			logger.info(f"Turning the heater OFF")
			pwm.ChangeDutyCycle(0)
			heater_on = False

		time.sleep(2)  # Adjust sampling rate as needed

except KeyboardInterrupt:
	print("Stopping...")
	pwm.stop()
	GPIO.cleanup()

