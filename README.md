# MLX90614 Infrared Temperature Sensor Reader for Raspberry Pi Reads temperature data via I2C interface

## Installation and Usage:
### 1. Install Dependencies:
~~~
# Install required Python library
pip3 install smbus2

# Enable I2C interface (if not already enabled)
sudo raspi-config
# Select: Interface Options -> I2C -> Yes
# Or use command line:
sudo apt-get install i2c-tools python3-smbus
~~~
### 2. Test I2C Connection:
~~~
# Check connected I2C devices
sudo i2cdetect -y 1
# You should see device at address 0x5A (MLX90614)
~~~
### 3. Run the Code:
~~~
# Main version with menu interface
python3 mlx90614_reader.py

# Simple command-line version
python3 simple_mlx.py --both --continuous --interval 0.5

# CSV output for data logging
python3 simple_mlx.py --both --format csv > temperature_log.csv
~~~
This code features:
1. I2C communication with MLX90614 sensor
2. 2-point calibration system
3. Exponential moving average filtering
4. Sensor configuration (emissivity, refresh rate, filter)
5. Temperature data logging






