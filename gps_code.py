'''
******READ BEFORE RUNNING*******
Summary of Code:
This code runs the IMU and GPS code simultaneously and displays their corresponding data.

If Running Code on Raspberry Pi Pico For First Time:
Only one Pi has all of the necessary installed and therefore is fully functional.
Working on the others will not work unless all of the libraries are there. See the 
transition document for more information on this.
There is also a specific wiring needed for everything, this would be in the transition document. 

Thing To Know When Modifying Code:
This code is running on CircuitPython (not MicroPython - they're slightly different),
therefore any modifications must be done in CircuitPython. It's not much different than
regular Python, it's just the implementation of modules that's wonky. Since it is running
on CircuitPython, only one file can be run at a time, so everything must be located here.
You can't reference multiple files, it will not work. 

Why did we choose CircuitPython instead of Micropython?:
We tried tirelessly to get the IMU to work with MicroPython - literally multiple hours
worth of work. We were not able to install the 'busio' library  in MicroPython so that
basically made it impossible to integrate the IMU. CircuitPython was the only way we got
the IMU to work. Unless you want to spend an outrageous amount of time getting the IMU 
integrated in MicroPython, I would suggest keeping it in CircuitPython.

Contact Info:
Drew Fowler: fowler52@purdue.edu
Paloma Arellano: palomasemailis@gmail.com
'''

import time
import busio
import board
import adafruit_bno055

INT_MAX = 10000

# Creates coordinate point struct
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    

# To determine if the coordinate/function q lies on the segment pr
def onSegment(p:tuple, q:tuple, r:tuple) -> bool:
    
    if((q[0] <= max(p[0], r[0])) &
       (q[0] >= min(p[0], r[0])) &
       (q[1] <= max(p[1], r[1])) &
       (q[1] >= min(p[1], r[1]))):
        return True
    return False

#Finding orientation
def orientation(p:tuple, q:tuple, r:tuple) -> int:
    
    val = (((q[1] - p[1]) * (r[0] - q[0])) - ((q[0] - p[0]) * (r[1] - q[1]))) #calculating slope
    
    if (val > 0):
        return 1 #positive slope is clockwise orientation
    elif (val < 0):
        return 2 #negative slope is counterclockwise orientation
    else:
        return 0 #collinear orientation
    

#Determine if line segment p1q1 and p2q2 intersects
def doIntersect(p1, q1, p2, q2):
    
    #looking for orientation
    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)
    
    #General Case: If the orientations are different, they intersect
    if (o1 != o2) and (o3 != o4):
        return True
    
    #Special Case (collinear): If x and y projection intersects, they intersect
    if (o1 == 0) and (onSegment(p1, p2, q1)): #p1, q1 and p2 are collinear and p2 lies on segment p1q1
        return True
    
    if (o2 == 0) and (onSegment(p1, q2, q1)): #p1, q1 and q2 are collinear and q2 lies on segment p1q1
        return True
    
    if (o3 == 0) and (onSegment(p2, p1, q2)): #p2, q2 and p1 are collinear and p1 lies on segment p2q2
        return True
    
    if (o4 == 0) and (onSegment(p2, q1, q2)): #p2, q2 and q1 are collinear and q1 lies on segment p2q2
        return True
    
    return False


#Determine if the point p lies within the polygon
def is_within_polygon(points:list, p:list) -> bool:
    
    n = len(points)
    if n < 3: #there must be at least 3 points/vertices in a polygon
        return False
    
    extreme = (INT_MAX, p[1]) #Create a point for line segment from p to infinite
    
    decrease = 0 #To calculate number of points where y-coordinate of the polygon is equal to y-coordinate of the point
    count = i = 0
    
    while True:
        next = (i + 1) % n
        
        if(points[i][1] == p[1]):
            decrease += 1
            
        if (doIntersect(points[i], points[next], p, extreme)):
            if orientation(points[i], p, points[next]) == 0:
                return onSegment(points[i], p, points[next])
                           
            count += 1
                           
        i = next
        
        if (i == 0):
            break
        
        count -= decrease
        
    return (count % 2 == 1)

"""
if __name__ == '__main__':
    polygon = [(40.430713, 86.915236),(40.430751, 86.915264),(40.430808, 86.915169),(40.430751, 86.915188)]
    p1 = [40.43120397177199, -86.91496015156082]
    if (is_within_polygon(polygon, p1)):
        print("True")
    else:
        print("False")
"""

# Turns on the LCD - currently not integrated correctly
# This function is still running on MicroPython so it would need to be changed to CircuitPython
def initialize_lcd(backlight_red, backlight_green, backlight_blue):
    #lcd_uart = UART(1, baudrate=9600, tx=Pin(4), rx=Pin(5))         # This line specifically should be changed to CircuitPython
    lcd_uart = busio.UART(board.GP4, board.GP5, baudrate=9600)
    lcd_uart.write(b'|')  # write 5 bytes
    lcd_uart.write(b'\x18')  # write 5 bytes
    lcd_uart.write(b'\x08')  # contrast
    lcd_uart.write(b'|')  # Put LCD into setting mode
    lcd_uart.write(b'\x2B')  # Set green backlight amount to 0%
    lcd_uart.write(backlight_red.to_bytes(1, 'big'))  # Set green backlight amount to 0%
    lcd_uart.write(backlight_green.to_bytes(1, 'big'))  # Set green backlight amount to 0%
    lcd_uart.write(backlight_blue.to_bytes(1, 'big'))  # Set green backlight amount to 0%
    lcd_uart.write(b'|')  # Setting character
    lcd_uart.write(b'-')  # Clear display
    return lcd_uart

# Initializes GPS
def initialize_gps():
    #return UART(0, baudrate=9600, tx=Pin(12), rx=Pin(13))
    return busio.UART(baudrate=9600, tx=board.GP12, rx=board.GP13, bits=8, stop=1, timeout=0, receiver_buffer_size=64)

# Gets Latitude
def get_latitude(str_array, index):
    latDeg = float(str_array[index][0: 2])
    latMin = float(str_array[index][2: 10]) / 60
    return '%f' % (float(latDeg) + float(latMin))

# Gets Longitude
def get_longitude(str_array, index2):
    longDeg = float(str_array[index2][1: 3])
    longMin = float(str_array[index2][3: 11]) / 60
    return '%f' % (float(longDeg) + float(longMin))

"""
def get_current_location(gps_uart):
    while True:
        while not gps_uart.any():
            pass
        time.sleep_ms(30)
        str_array = gps_uart.readline()
        print(str_array)
        try:
            str_array = str_array.decode("utf-8")
            time.sleep_ms(30)
            str_array = str_array.split(",")
            print(str_array)
        except:
            pass
        
        if str_array[0] is '$GPGLL':
            #print(str_array)
            #str_array = str_array.split(",")
            print("in GPGLL")
            #lcd_uart.write("in GNGLL")
            latitude = get_latitude(str_array, 1)
            longitude = get_longitude(str_array, 3)
            print("in GPGLL2")
            #lcd_uart.write("in GNGLL2")

        elif str_array[0] is '$GPGGA':
            print("in GNPGA")
            #lcd_uart.write("in GNGGA")
            latitude = get_latitude(str_array, 2)
            longitude = get_longitude(str_array, 4)
            print("in GPGGA2")
            return latitude, longitude
"""
# Gets Current Location
def get_current_location(gps_uart):
    latitude_avg = 0
    longitude_avg = 0
    for i in range(0, 10):
        latitude = 0
        longitude = 0
        
        while True:
            
            time.sleep(0.03)
            str_array = gps_uart.readline()
            if str_array is None:
                break
            try:
                str_array = str_array.decode("utf-8")       # Decodes GPS input
                time.sleep(0.03)
                str_array = str_array.split(",")
                #print(str_array)                            # Prints GPS Output
            except:
                pass
            
            
            if str_array[0] is '$GPGLL':
                #print("in GPGLL")
                #lcd_uart.write("in GNGLL")
                latitude = get_latitude(str_array, 1)
                longitude = get_longitude(str_array, 3)
                #print("in GPGLL2: Latitude: ", latitude + "  Longitude: ", longitude)
                break
                #lcd_uart.write("in GNGLL2")

            elif str_array[0] is '$GPGGA':
                #print("in GPGGA")
                #lcd_uart.write("in GNGGA")
                latitude = get_latitude(str_array, 2)
                longitude = get_longitude(str_array, 4)
                #print("in GPGGA2: Latitude: ", latitude  + "  Longitude: ", longitude)
                break
            
        latitude_avg = float(latitude_avg) + float(latitude)
        longitude_avg = float(longitude_avg) + float(longitude)
        
    latitude_avg /= 2
    longitude_avg /= 2
    
    return latitude_avg, longitude_avg

# Gets Temperature from IMU
def temperature():
  global last_val  # pylint: disable=global-statement
  result = sensor.temperature
  if abs(result - last_val) == 128:
    result = sensor.temperature
    if abs(result - last_val) == 128:
      return 0b00111111 & result
  last_val = result
  return result

# Displays IMU sensor information
def imu_stuff():
  '''
  print("Temperature: {} degrees C".format(sensor.temperature))
  print("Accelerometer (m/s^2): {}".format(sensor.acceleration))
  print("Magnetometer (microteslas): {}".format(sensor.magnetic))
  print("Gyroscope (rad/sec): {}".format(sensor.gyro))
  print("Euler angle: {}".format(sensor.euler))
  print("Quaternion: {}".format(sensor.quaternion))
  print("Linear acceleration (m/s^2): {}".format(sensor.linear_acceleration))
  print("Gravity (m/s^2): {}".format(sensor.gravity))
  print()
  time.sleep(1)
  '''

if __name__ == '__main__':

    i2c = busio.I2C(board.GP15, board.GP14, frequency=400000)       # Initializes I2C for the IMU
    sensor = adafruit_bno055.BNO055_I2C(i2c)                        # Initializes IMU

    last_val = 0xFFFF
    
    gps_uart = initialize_gps()                                     # Initializes GPS
    lcd_uart = initialize_lcd(backlight_red=255, backlight_green=1, backlight_blue=255)
    
    lcd_uart.write(b"Connecting to GPS...            ")  # For 16x2 LCD
    time.sleep(1.5)
    
    # Example Polygon that currently does nothing
    polygon = [
    (40.430484, 86.915721),
    (40.430454, 86.915769),
    (40.430806, 86.916144),
    (40.430835, 86.916097)
    ]
    
    while True:
        try:
            startTime = time.monotonic()
            imu_stuff()                                                     # Displays IMU Stuff
            time.sleep(0.3)
            latitude_avg, longitude_avg = get_current_location(gps_uart)    # Gets location info

            lcd_uart.write(b"EPICS EVEI                      ")  # For 16x2 LCD
            time.sleep(1.5)
            #lcd_uart.write(b'                ')  # Clear display
            print("Latitude: ", str(latitude_avg) + "  Longitude: ", str(longitude_avg))    # Prints Lat and Long Info
            
            if is_within_polygon(polygon, (float(latitude_avg), float(longitude_avg))) is True:
                
                lcd_uart.write(b"IN                              ")  # For 16x2 LCD
            else:
                
                lcd_uart.write(b"OUT                             ")  # For 16x2 LCD
            
            #lcd_uart.write(b'                ')  # Clear display
            
            ###### This would print the information to the LCD - which is currently in MicroPython and does not work
            #time.sleep(1.5)
            #lcd_uart.write(b"Current Location:               ")  # For 16x2 LCD
            #time.sleep(1.5)
            #lcd_uart.write(b"Lat:  ")  # For 16x2 LCD
            #lcd_uart.write(latitude_avg.to_bytes(10, "big"))
            #print(latitude_avg.to_bytes(10, "big"))
            #lcd_uart.write(b" N   ")
            #time.sleep(1.5)
            #lcd_uart.write(b"Long: " + bytes(longitude_avg) + b" W   ")  # For 16x2 LCD
            #time.sleep(1.5)
            
            #lcd_uart.write(b'                ')  # Clear display
            
            endTime = time.monotonic()
            print("GPS Refresh Rate: ", float(endTime - startTime))
        except (ValueError):
            print("ValueError: Likely weak signal, try testing outside")

