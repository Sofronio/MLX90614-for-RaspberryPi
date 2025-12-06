#!/usr/bin/env python3
"""
Simple MLX90614 temperature reader for Raspberry Pi
Command-line interface for easy integration
"""

import smbus2
import time
import argparse

class SimpleMLX90614:
    def __init__(self, address=0x5A, bus=1):
        self.bus = bus
        self.address = address
        self.i2c = None
        
    def connect(self):
        """Connect to the sensor"""
        try:
            self.i2c = smbus2.SMBus(self.bus)
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def read_temperature(self, register):
        """Read temperature from specified register"""
        try:
            data = self.i2c.read_i2c_block_data(self.address, register, 3)
            value = (data[1] << 8) | data[0]
            temp_kelvin = value * 0.02
            temp_celsius = temp_kelvin - 273.15
            return round(temp_celsius, 2)
        except:
            return None
    
    def read_object_temp(self):
        """Read object temperature"""
        return self.read_temperature(0x07)
    
    def read_ambient_temp(self):
        """Read ambient temperature"""
        return self.read_temperature(0x06)

def main():
    parser = argparse.ArgumentParser(description='Read MLX90614 temperature sensor')
    parser.add_argument('--object', '-o', action='store_true', help='Read object temperature')
    parser.add_argument('--ambient', '-a', action='store_true', help='Read ambient temperature')
    parser.add_argument('--both', '-b', action='store_true', help='Read both temperatures')
    parser.add_argument('--continuous', '-c', action='store_true', help='Continuous reading')
    parser.add_argument('--interval', '-i', type=float, default=1.0, help='Continuous read interval in seconds')
    parser.add_argument('--format', '-f', choices=['simple', 'csv', 'json'], default='simple', help='Output format')
    
    args = parser.parse_args()
    
    sensor = SimpleMLX90614()
    
    if not sensor.connect():
        print("Failed to connect to sensor. Check:")
        print("1. I2C is enabled: sudo raspi-config -> Interface Options -> I2C")
        print("2. Wiring: SDA->GPIO2, SCL->GPIO3, VCC->3.3V, GND->GND")
        return
    
    if args.continuous:
        print("Continuous reading (Press Ctrl+C to stop)")
        try:
            while True:
                if args.object or not (args.object or args.ambient or args.both):
                    obj_temp = sensor.read_object_temp()
                    if args.format == 'csv':
                        print(f"{time.time()},{obj_temp}")
                    elif args.format == 'json':
                        print(f'{{"timestamp": {time.time()}, "object_temp": {obj_temp}}}')
                    else:
                        print(f"Object temperature: {obj_temp}°C")
                        
                if args.ambient:
                    amb_temp = sensor.read_ambient_temp()
                    if args.format == 'csv':
                        print(f"{time.time()},{amb_temp}")
                    elif args.format == 'json':
                        print(f'{{"timestamp": {time.time()}, "ambient_temp": {amb_temp}}}')
                    else:
                        print(f"Ambient temperature: {amb_temp}°C")
                        
                if args.both:
                    obj_temp = sensor.read_object_temp()
                    amb_temp = sensor.read_ambient_temp()
                    if args.format == 'csv':
                        print(f"{time.time()},{obj_temp},{amb_temp}")
                    elif args.format == 'json':
                        print(f'{{"timestamp": {time.time()}, "object_temp": {obj_temp}, "ambient_temp": {amb_temp}}}')
                    else:
                        print(f"Object: {obj_temp}°C, Ambient: {amb_temp}°C")
                
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped reading")
    else:
        if args.object or not (args.object or args.ambient or args.both):
            obj_temp = sensor.read_object_temp()
            print(f"Object temperature: {obj_temp}°C")
        if args.ambient:
            amb_temp = sensor.read_ambient_temp()
            print(f"Ambient temperature: {amb_temp}°C")
        if args.both:
            obj_temp = sensor.read_object_temp()
            amb_temp = sensor.read_ambient_temp()
            print(f"Object temperature: {obj_temp}°C")
            print(f"Ambient temperature: {amb_temp}°C")

if __name__ == "__main__":
    main()simple_mlx.py
