import datetime
import os.path
import os
import time
import pygame
import sys
import threading
import time

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt5.QtCore import QTimer
from queue import Queue


from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError



# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

with open("CalendarID.txt", "r") as calendar_id_file: 
    calendar_id = calendar_id_file.read()

def fetch_events(service):
    now = datetime.datetime.utcnow().isoformat() + "Z"
    event_result = service.events().list(
        calendarId=calendar_id,
        timeMin=now,
        maxResults=10,
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    return event_result.get("items", [])


def check_events(service, event_queue):
    last_fetch_time = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    fetch_inverval = datetime.timedelta(minutes=10)
    check_interval = 60 # 1 minute
    events = []

    
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        
        if now - last_fetch_time >= fetch_inverval:
            events = fetch_events(service)
            event_queue.put(events)
            last_fetch_time = now
            
        for event in events:
            start_str = event["start"].get("dateTime", event["start"].get("date"))
            start = datetime.datetime.fromisoformat(start_str)
            if now >= start:
                set_volume(0.5)
                play_alarm_sound("Assets/Alarm_sound.mp3")
                events.remove(event)

        time.sleep(check_interval)

pygame.mixer.init()    
    
def play_alarm_sound(sound_file):
    pygame.mixer.music.load(sound_file)
    pygame.mixer.music.play(-1)
    
def set_volume(volume_level): # volume_level: float between 0.0 and 1.0
    pygame.mixer.music.set_volume(volume_level)
    
    
def stop_alarm():
    if pygame.mixer.music.get_busy(): # check if alarm is playing
        pygame.mixer.music.stop()


def create_gui(event_queue, service):
    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("Google Calendar Alarm")
    
    layout = QVBoxLayout()
    
    events = []
    
    stop_button = QPushButton("Stop Alarm", window)
    stop_button.clicked.connect(stop_alarm)
    layout.addWidget(stop_button)
    
    refetch_button = QPushButton("Refetch Events", window)
    layout.addWidget(refetch_button)
    
    def refetch_events():
        reply = QMessageBox.question(window, "Confirm Refetch", "Are you sure you want to refetch events?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            events = fetch_events(service)
            event_queue.put(events)
            
    refetch_button.clicked.connect(refetch_events)
    
    def update_events():
        nonlocal events
        if not event_queue.empty():
            events = event_queue.get()
        
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget is not None and widget not in [stop_button, refetch_button]:
                widget.deleteLater()
                
        for event in events:
            summary = event.get('summary', 'No title')
            start = event['start'].get('dateTime', event['start'].get('date','No Start Time'))
            event_info = f"{summary} at {start}"
            label = QLabel(event_info)
            layout.addWidget(label)
        
    
    timer = QTimer() 
    timer.timeout.connect(update_events)
    timer.start(1000)
    
    window.setLayout(layout)
    window.show()
    sys.exit(app.exec_())
    
    
    

    

def main():
  """Shows basic usage of the Google Calendar API.
  Prints the start and name of the next 10 events on the user's calendar.
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    service = build("calendar", "v3", credentials=creds)

    event_queue = Queue()
    event_thread = threading.Thread(target=check_events, args=(service, event_queue))
    event_thread.start()
    create_gui(event_queue, service)

  except HttpError as error:
    print(f"An error occurred: {error}")


if __name__ == "__main__":
  main()
  
