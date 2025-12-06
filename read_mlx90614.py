#!/usr/bin/env python3
"""
MLX90614 Infrared Temperature Sensor Reader for Raspberry Pi
Reads temperature data via I2C interface
"""

import smbus2
import time
import struct
import math

class MLX90614:
    def __init__(self, address=0x5A, bus=1):
        """
        Initialize MLX90614 sensor
        
        Args:
            address: I2C address (default 0x5A)
            bus: I2C bus number (Raspberry Pi default is 1)
        """
        self.bus = smbus2.SMBus(bus)
        self.address = address
        
        # Initialize filter variables
        self.filt_temp_c = None
        self.alpha = 0.20  # Filter coefficient
        
        # Calibration parameters
        self.cal_low = None
        self.cal_high = None
        self.cal_raw_low = None
        self.cal_raw_high = None
        
        # Configuration constants (matching Arduino code)
        self.target_emissivity = 0.98
        self.target_refresh_code = 0x04  # 32 Hz
        self.target_filter_code = 0x33   # Fast averaging
        
        # Load calibration data from file
        self._load_calibration_from_file()
        
    def _read_word(self, register):
        """
        Read a word (16-bit) from the sensor
        """
        try:
            # MLX90614 requires reading 3 bytes: data low, data high, PEC
            data = self.bus.read_i2c_block_data(self.address, register, 3)
            value = (data[1] << 8) | data[0]  # Little-endian: low byte first
            return value
        except Exception as e:
            print(f"Failed to read register {hex(register)}: {e}")
            return None
    
    def _write_word(self, register, value):
        """
        Write a word (16-bit) to the sensor
        """
        try:
            # MLX90614 write requires 4 bytes: command, address, data low, data high
            self.bus.write_i2c_block_data(self.address, 0x2E, 
                                          [register, value & 0xFF, (value >> 8) & 0xFF])
            time.sleep(0.01)  # Wait 10ms
            return True
        except Exception as e:
            print(f"Failed to write register {hex(register)}: {e}")
            return False
    
    def _read_eeprom(self, addr):
        """
        Read EEPROM data
        """
        return self._read_word(0x20 | addr)
    
    def _write_eeprom(self, addr, value):
        """
        Write EEPROM data
        """
        return self._write_word(addr, value)
    
    def ensure_config(self):
        """
        Ensure sensor configuration is correct (same logic as Arduino code)
        """
        # Check and set emissivity
        raw_em = self._read_eeprom(0x24)
        if raw_em is not None:
            current_em = raw_em / 65535.0
            if abs(current_em - self.target_emissivity) > 0.005:
                target_value = int(self.target_emissivity * 65535.0)
                if self._write_eeprom(0x24, target_value):
                    print(f"Emissivity set to: {self.target_emissivity}")
        
        # Check and set refresh rate
        raw_ref = self._read_eeprom(0x04)
        if raw_ref is not None and (raw_ref & 0x07) != self.target_refresh_code:
            if self._write_eeprom(0x04, self.target_refresh_code):
                print(f"Refresh rate set to 32Hz")
        
        # Check and set filter
        raw_filt = self._read_eeprom(0x05)
        if raw_filt is not None and (raw_filt & 0xFF) != self.target_filter_code:
            if self._write_eeprom(0x05, self.target_filter_code):
                print(f"Filter set to fast averaging mode")
    
    def read_object_temp_c(self):
        """
        Read object temperature in Celsius
        """
        try:
            # Read TOBJ1 register (0x07) - Object temperature
            data = self._read_word(0x07)
            if data is None:
                return None
            
            # Convert temperature: data * 0.02 - 273.15
            temp_kelvin = data * 0.02
            temp_celsius = temp_kelvin - 273.15
            
            return round(temp_celsius, 2)
        except Exception as e:
            print(f"Failed to read object temperature: {e}")
            return None
    
    def read_ambient_temp_c(self):
        """
        Read ambient temperature in Celsius
        """
        try:
            # Read TA register (0x06) - Ambient temperature
            data = self._read_word(0x06)
            if data is None:
                return None
            
            # Convert temperature: data * 0.02 - 273.15
            temp_kelvin = data * 0.02
            temp_celsius = temp_kelvin - 273.15
            
            return round(temp_celsius, 2)
        except Exception as e:
            print(f"Failed to read ambient temperature: {e}")
            return None
    
    def read_emissivity(self):
        """
        Read current emissivity setting
        """
        raw_em = self._read_eeprom(0x24)
        if raw_em is not None:
            return round(raw_em / 65535.0, 4)
        return None
    
    def _load_calibration_from_file(self, filename="calibration.txt"):
        """
        Load calibration parameters from file
        """
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
                if len(lines) >= 4:
                    self.cal_low = float(lines[0].strip())
                    self.cal_high = float(lines[1].strip())
                    self.cal_raw_low = float(lines[2].strip())
                    self.cal_raw_high = float(lines[3].strip())
                    print(f"Calibration data loaded from {filename}")
        except FileNotFoundError:
            print(f"Calibration file {filename} not found, using raw data")
        except Exception as e:
            print(f"Failed to load calibration data: {e}")
    
    def _save_calibration_to_file(self, filename="calibration.txt"):
        """
        Save calibration parameters to file
        """
        try:
            with open(filename, 'w') as f:
                f.write(f"{self.cal_low}\n")
                f.write(f"{self.cal_high}\n")
                f.write(f"{self.cal_raw_low}\n")
                f.write(f"{self.cal_raw_high}\n")
            print(f"Calibration data saved to {filename}")
        except Exception as e:
            print(f"Failed to save calibration data: {e}")
    
    def apply_calibration(self, raw_temp):
        """
        Apply 2-point calibration
        """
        if (self.cal_low is None or self.cal_high is None or 
            self.cal_raw_low is None or self.cal_raw_high is None):
            return raw_temp
        
        if abs(self.cal_raw_high - self.cal_raw_low) < 0.001:
            return raw_temp
        
        scale = (self.cal_high - self.cal_low) / (self.cal_raw_high - self.cal_raw_low)
        offset = self.cal_low - self.cal_raw_low * scale
        
        calibrated_temp = raw_temp * scale + offset
        return round(calibrated_temp, 2)
    
    def calibrate_2_point(self, cold_temp, hot_temp):
        """
        Perform 2-point calibration
        
        Args:
            cold_temp: Cold reference temperature (°C)
            hot_temp: Hot reference temperature (°C)
        """
        print("\n=== Starting 2-Point Calibration ===")
        
        # Read cold point raw temperature
        print(f"Please point sensor at cold reference ({cold_temp}°C)")
        input("Press Enter when ready...")
        
        raw_cold = self.read_object_temp_c()
        if raw_cold is None:
            print("Failed to read cold point temperature")
            return False
        
        # Read hot point raw temperature
        print(f"\nPlease point sensor at hot reference ({hot_temp}°C)")
        input("Press Enter when ready...")
        
        raw_hot = self.read_object_temp_c()
        if raw_hot is None:
            print("Failed to read hot point temperature")
            return False
        
        # Save calibration parameters
        self.cal_low = cold_temp
        self.cal_high = hot_temp
        self.cal_raw_low = raw_cold
        self.cal_raw_high = raw_hot
        
        # Save to file
        self._save_calibration_to_file()
        
        print("\n=== Calibration Complete ===")
        print(f"Cold point: Raw {raw_cold:.2f}°C -> Calibrated {cold_temp:.2f}°C")
        print(f"Hot point:  Raw {raw_hot:.2f}°C -> Calibrated {hot_temp:.2f}°C")
        print("============================\n")
        
        return True
    
    def get_filtered_temperature(self):
        """
        Get filtered temperature values with exponential moving average
        """
        raw_temp = self.read_object_temp_c()
        if raw_temp is None:
            return None
        
        # Apply exponential moving average filter
        if self.filt_temp_c is None:
            self.filt_temp_c = raw_temp
        else:
            self.filt_temp_c = self.alpha * raw_temp + (1.0 - self.alpha) * self.filt_temp_c
        
        # Apply calibration
        calibrated_temp = self.apply_calibration(self.filt_temp_c)
        
        return {
            'raw': raw_temp,
            'filtered': round(self.filt_temp_c, 2),
            'calibrated': calibrated_temp
        }


def main():
    """
    Main function - Example usage
    """
    print("MLX90614 Infrared Temperature Sensor Test")
    print("==========================================")
    
    try:
        # Initialize sensor
        sensor = MLX90614(address=0x5A, bus=1)
        
        # Check sensor connection
        print("Checking sensor connection...")
        temp = sensor.read_object_temp_c()
        if temp is None:
            print("Error: Cannot connect to MLX90614 sensor, please check wiring")
            return
        
        print("Sensor connected successfully!")
        
        # Ensure correct configuration
        sensor.ensure_config()
        
        # Display current emissivity
        emissivity = sensor.read_emissivity()
        if emissivity is not None:
            print(f"Current emissivity: {emissivity}")
        
        print("\nCommand Options:")
        print("  r - Real-time temperature reading")
        print("  c - 2-point calibration")
        print("  t - Single temperature reading")
        print("  s - Sensor information")
        print("  q - Quit")
        print("==========================================\n")
        
        while True:
            command = input("Enter command (r/c/t/s/q): ").strip().lower()
            
            if command == 'q':
                print("Exiting program")
                break
                
            elif command == 'r':
                print("\nStarting real-time reading (Press Ctrl+C to stop)")
                try:
                    while True:
                        temps = sensor.get_filtered_temperature()
                        ambient = sensor.read_ambient_temp_c()
                        if temps is not None:
                            print(f"Raw: {temps['raw']:.2f}°C | "
                                  f"Filtered: {temps['filtered']:.2f}°C | "
                                  f"Calibrated: {temps['calibrated']:.2f}°C | "
                                  f"Ambient: {ambient:.2f}°C")
                        time.sleep(0.1)  # 100ms interval
                except KeyboardInterrupt:
                    print("\nStopped real-time reading")
                    
            elif command == 'c':
                try:
                    cold_temp = float(input("Enter cold reference temperature (°C): "))
                    hot_temp = float(input("Enter hot reference temperature (°C): "))
                    sensor.calibrate_2_point(cold_temp, hot_temp)
                except ValueError:
                    print("Error: Please enter valid numbers")
                except KeyboardInterrupt:
                    print("\nCalibration cancelled")
                    
            elif command == 't':
                temps = sensor.get_filtered_temperature()
                ambient = sensor.read_ambient_temp_c()
                if temps is not None:
                    print(f"\nSingle Reading:")
                    print(f"  Raw:        {temps['raw']:.2f}°C")
                    print(f"  Filtered:   {temps['filtered']:.2f}°C")
                    print(f"  Calibrated: {temps['calibrated']:.2f}°C")
                    print(f"  Ambient:    {ambient:.2f}°C")
                else:
                    print("Failed to read temperature")
                    
            elif command == 's':
                print(f"\nSensor Information:")
                print(f"  I2C Address: 0x{sensor.address:02X}")
                emissivity = sensor.read_emissivity()
                print(f"  Emissivity:  {emissivity}")
                print(f"  Calibration: {'Loaded' if sensor.cal_low else 'Not loaded'}")
                
            else:
                print("Unknown command")
                
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"Program error: {e}")


if __name__ == "__main__":
    # First ensure I2C is enabled
    print("Note: Please ensure I2C is enabled on your Raspberry Pi")
    print("Enable command: sudo raspi-config -> Interface Options -> I2C -> Yes")
    print("Or run: sudo apt-get install i2c-tools python3-smbus\n")
    
    main()
