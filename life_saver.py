# Twilio is the 3rd party service used to make
# phone calls and send messages
from twilio.rest import TwilioRestClient

# Library used for handling dates
from datetime import datetime

# Library for using delay
import time

# library to communicate with arduino
# through serial (USB)
import serial

# Libraries for communicating with OLED display
import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

# Libraries for creating the image and text to be
# displayed on OLED
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

#import signal

# To convert lat and lon to user friendly places
import googlemaps

# To create threads
import threading

# Class to communicate with arduino
class Sensor:
    # Initialize the serial port
    def __init__(self, device = '/dev/serial/by-id/usb-1a86_USB2.0-Serial-if00-port0', baud_rate = 9600, debug_print = False):
        self.device = device
        self.baud_rate = baud_rate
        self.debug_print = debug_print
        self.ser = serial.Serial(self.device, self.baud_rate)
        # Toggle DTR to reset Arduino
        self.ser.setDTR(False)
        time.sleep(1)
        self.ser.flushInput()
        self.ser.setDTR(True)
        self.ser.flushInput()
        self.ser.flushOutput()

    # Read the serial data from arduino and parse the sensor data
    def get_sensor_data(self):
        raw_sensor_data = self.ser.readline()

        if(self.debug_print):
            print raw_sensor_data

        sensor_data_list = raw_sensor_data.strip("\r\n").split(" ")

        acc_x = int(sensor_data_list[0].split("Acc:")[1])
        lat = str(sensor_data_list[1].split("Lat:")[1])
        lon = str(sensor_data_list[2].split("Lon:")[1])

        return acc_x, lat, lon

    # Clear the buffers, for a fresh start
    def flush(self):
        self.ser.flushInput()
        self.ser.flushOutput()

    # Close the serial port on exit
    def __del__(self):
        self.flush()
        self.ser.close()

# Class for handling OLED display
class OLED:
    # Constructor to initalize the OLED display
    def __init__(self, rst_pin = 24, bit_depth = 1, font_type = '', font_size = 18):
        # Initalize the Adafruit SSD1306 library
        self.disp = Adafruit_SSD1306.SSD1306_128_64(rst = rst_pin)
        self.disp.begin()

        # Get the dimesnsions of the OLED display
        self.width = self.disp.width
        self.height = self.disp.height

        # Create an image instance
        # Since it is a monochrome display bit depth is 1
        self.image = Image.new(str(bit_depth), (self.width, self.height))

        # Clear the display
        self.disp.clear()
        self.disp.display()

        # Set the font type and size, if specified
        if(font_type):
            self.font = ImageFont.truetype(font_type, font_size)
        else:
            self.font = ImageFont.load_default()

        # Create the draw instance, used to draw on the OLED display
        self.draw = ImageDraw.Draw(self.image)

    # Function to clear the OLED screen
    def clear(self):
        self.draw.rectangle((0, 0, self.width, self.height), outline = 0, fill = 0)

    # Function to clear a row on the OLED screen
    def clear_row(self, row):
        self.draw.rectangle((0, row, self.width, self.height), outline = 0, fill = 0)

    # Function to display text on the OLED screen
    def display(self, pos, text, alpha = 255):
        self.draw.text(pos, text, font = self.font, fill = alpha)
        self.disp.image(self.image)
        self.disp.display()

    def __del__(self):
        # Clear the display
        self.disp.clear()
        self.disp.display()

# Progress bar
def progress(screen):
    screen.clear_row(45)
    screen.display((40 ,40), ".")
    screen.display((45 ,40), ".")
    screen.display((50 ,40), ".")
    screen.display((55 ,40), ".")
    screen.display((60 ,40), ".")
    screen.display((65 ,40), ".")
    screen.display((70 ,40), ".")
    screen.display((75 ,40), ".")
    screen.display((80 ,40), ".")

# Home screen
def home_screen(screen):
    screen.clear()
    screen.display((7, 0), "Monitoring")
    screen.display((40 ,20), "Car")
    progress(screen)

# Screen to be displayed, when accident is detected
def accident_detected_screen(screen):
    screen.clear()
    screen.display((7, 10), "Emergency")
    screen.display((7, 30), "Broadcast")

# Screen to display countdown
def countdown_screen(screen):
    countdown = 10
    while(countdown >= 0):
        screen.clear()
        screen.display((48,0), str(countdown))
        countdown -= 1
        time.sleep(1)

# Screen that displays Calling for help
def calling_help_screen(screen):
    screen.clear()
    screen.display((7, 0), "Calling")
    screen.display((7, 20), "For")
    screen.display((7, 40), "Help !!!")

# Screen displayed after successfull broadcast
def calling_help_success_screen(screen):
    screen.clear()
    screen.display((7, 0), "Help Will")
    screen.display((7, 20), "Arrive")
    screen.display((7, 40), "Shortly...")

# Screen displayed during restart
def restarting_screen(screen):
    screen.clear()

# Manual restart required
def manual_restart_screen(screen):
    screen.clear()
    screen.display((7, 0), "Manual")
    screen.display((7, 20), "Restart")
    screen.display((7, 40), "Required...")

# Class to handle accident detection and notification
class Twilio:
    def __init__(self):
        # Twilio account details
        self.account_sid = "ACee1e2fcd3d78d43b31d37fcff00debc2"
        self.auth_token  = "07557fc2fc9533b6d1c862ff77de1088"
        self.account_phone_number =  "+12014823878"
        self.call_pickup_url = "http://twimlets.com/holdmusic?Bucket=com.twilio.music.ambient"
        self.call_ring_timeout_s = 20
        self.failed_recipient_list = list()
        self.recipient_list = list()
        self.total_recipients = 10
        self.utc_start_time = datetime.utcnow()

        # Create the twilio client that will communicate
        # with the twilio server
        self.twilio_client = TwilioRestClient(self.account_sid, self.auth_token)
        self.get_broadcast_list()

    # Get the list of registered phone numbers from the server
    def get_broadcast_list(self):
        caller_ids = self.twilio_client.caller_ids.list()

        for caller_id in self.twilio_client.caller_ids.iter():
            phone_number = '+' + str(caller_id.friendly_name)
            if phone_number not in self.recipient_list:
                self.recipient_list.append(phone_number)

        self.total_recipients = len(self.recipient_list)

        return self.recipient_list

    def broadcast_emergency_message(self, message, recipient_list):
        for phone_number in recipient_list:
            print 'Sending SMS ', phone_number
            self.twilio_client.messages.create(to = phone_number, from_ = self.account_phone_number, body = message)
            time.sleep(1)

    def broadcast_emergency_call(self, recipient_list):
        self.utc_start_time = datetime.utcnow()
        self.call_status = dict()
        for phone_number in recipient_list:
            print 'Calling ', phone_number
            self.twilio_client.calls.create(to = phone_number, from_= self.account_phone_number, url= self.call_pickup_url, timeout = self.call_ring_timeout_s)
            time.sleep(2)
            self.call_status[phone_number] = "queued"

        return self.call_status

    def update_call_status(self):
        del self.failed_recipient_list[:]
        for call_log in self.twilio_client.calls.list(started_after = self.utc_start_time, PageSize = self.total_recipients):
            if(self.utc_start_time < datetime.strptime(call_log.start_time.split(" +")[0], "%a, %d %b %Y %H:%M:%S")):
                if(call_log.to_formatted in self.call_status):
                    self.call_status[call_log.to_formatted] = str(call_log.status)
                if((call_log.status != "completed") and (call_log.to_formatted not in self.failed_recipient_list)):
                    self.failed_recipient_list.append(call_log.to_formatted)
                print(" To: " + call_log.to_formatted + " Status: " + call_log.status + " Start Time: " + call_log.start_time.split(" +")[0])

        return self.failed_recipient_list

# Function to broadcast emergency calls and message,
# this will try to broadcast the calls until it is
# picked up by the user
def broadcast_emergency(twilio_client, message):
    twilio_client.broadcast_emergency_message(message, twilio_client.recipient_list)
    twilio_client.broadcast_emergency_call(twilio_client.recipient_list)
    retry_failed_calls = True
    while(retry_failed_calls):
        time.sleep(30)
        failed_recipient_list = twilio_client.update_call_status()
        if failed_recipient_list:
            print 'Retrying Calls', failed_recipient_list
            twilio_client.broadcast_emergency_call(failed_recipient_list)
        else:
            break;

#Function to use google reverse lookup
def reverse_gps_lookup(lat, long):
    try:
        gmaps = googlemaps.Client(key='AIzaSyBMiCLiRo2vjKWsu4Tsc9W4U2wOKv_ODRk')
        reverse_geocode_result = gmaps.reverse_geocode((lat, long))
        return str(reverse_geocode_result[0]['formatted_address'])
    except:
        return ''

# This is the main function that monitors the vehicle
def monitor_vehicle():
    # Initialize all the modules
    arduino_nano = Sensor()
    general_profile = OLED(font_type = '/home/pi/life_saver/Starjedi.ttf', font_size = 18)
    countdown_profile = OLED(font_type = '/home/pi/life_saver/Starjedi.ttf', font_size = 40)

    # Display the home screen
    print 'Monitoring Vehicle...'
    #home_screen(general_profile)
    home_screen_thread = threading.Thread(target=home_screen, args=(general_profile, ))
    try:
        acc_x, lat, lon = arduino_nano.get_sensor_data()
        if not acc_x:
            manual_restart_screen(general_profile)
            while(1):
                pass
    except Exception as e:
        print e
    # Run indefinitely
    while(1):
        try:
            # Get the data from the arduino
            if not home_screen_thread.isAlive():
                home_screen_thread = threading.Thread(target=home_screen, args=(general_profile, ))
                home_screen_thread.start()
            acc_x, lat, lon = arduino_nano.get_sensor_data()
            # if acceleration exceeds the threshold, Call For Help !!!
            if(abs(acc_x) > 28000):
                print 'Crash Detected...'
                home_screen_thread.join()
                # Display the Emergency Broadcast screen
                accident_detected_screen(general_profile)
                time.sleep(2)
                # Start the countdown, this is to give time to the
                # user to reset a false alarn
                countdown_screen(countdown_profile)
                # If the user does not reset the alarm, then call for help indefinitely
                # until help arrives
                while(1):
                    try:
                        # Display the Calling For Help screen
                        calling_help_screen(general_profile)
                        twilio_client = Twilio()
                        # Compile the SMS with link to google maps
                        message = ''
                        retry_sms = True
                        if(lat == "0.0" and lon == "0.0"):
                            message = "Accident!,Trying to get location"
                        else:
                            message = "Accident!, http://maps.google.com/maps?q={},{} {}".format(lat, lon, reverse_gps_lookup(lat, lon))
                            retry_sms = False
                        print message
                        twilio_client.broadcast_emergency_message(message, twilio_client.recipient_list)
                        twilio_client.broadcast_emergency_call(twilio_client.recipient_list)

                        while(True):
                            try:
                                time.sleep(30)

                                if(retry_sms):
                                    print 'Trying to get location...'
                                    acc_x, lat, lon = arduino_nano.get_sensor_data()
                                    if(lat != "0.0" or lon != "0.0"):
                                        message = "Accident!, http://maps.google.com/maps?q={},{} {}".format(lat, lon, reverse_gps_lookup(lat, lon))
                                        print message
                                        twilio_client.broadcast_emergency_message(message, twilio_client.recipient_list)
                                        retry_sms = False

                                failed_recipient_list = twilio_client.update_call_status()
                                if failed_recipient_list:
                                    print 'Retrying Calls', failed_recipient_list
                                    twilio_client.broadcast_emergency_call(failed_recipient_list)

                                if(retry_sms == False and not failed_recipient_list):
                                    break
                            except Exception as e:
                                print e

                        # Display the screen, that shows help is on its way
                        calling_help_success_screen(general_profile)
                        # Reset the data and go back to monitoring the vehicle
                        acc_x = 0
                        arduino_nano.flush()
                        # Wait 5 seconds before going back to monitoring vehicle
                        time.sleep(5)
                        break;
                    except Exception as e:
                        print e
                print 'Monitoring Vehicle...'
        except Exception as e:
            print e
"""
def signal_handler(signal, frame):
    general_profile = OLED(font_type = '/home/pi/life_saver/Starjedi.ttf', font_size = 18)
    restarting_screen(general_profile)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
"""
# Start of execution
if __name__ == '__main__':
    monitor_vehicle()
