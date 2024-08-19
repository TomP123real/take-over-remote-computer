import socket
import threading
import keyboard
import pyautogui
import mouse
import time
import io
from PIL import Image
import tkinter as tk
from PIL import ImageTk

def send_actions(host, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((host, port))
        print(f"Connected to {host}:{port} for sending actions")
    except Exception as e:
        print(f"Error connecting to server for actions: {e}")
        return

    screen_width, screen_height = pyautogui.size()

    def on_key_event(event):
        try:
            client_socket.send(f"KEY:{event.name}".encode())
        except Exception as e:
            pass 

    def listen_for_mouse_events():
        previous_x, previous_y = pyautogui.position()
        while True:
            try:
                x, y = pyautogui.position()
                if (x, y) != (previous_x, previous_y):
                    mapped_x = int(x * 1920 / screen_width)  
                    mapped_y = int(y * 1080 / screen_height) 
                    client_socket.send(f"MOUSE:MOVE:{mapped_x},{mapped_y}".encode())
                    previous_x, previous_y = x, y
                time.sleep(0.1)
            except BrokenPipeError:
                break
            except Exception as e:
                break

    def on_mouse_click(event):
        try:
            if event.event_type == 'down':  
                button = event.button
                client_socket.send(f"MOUSE:CLICK:{button}".encode())
        except Exception as e:
            pass  

    keyboard.on_press(on_key_event)
    
    mouse_thread = threading.Thread(target=listen_for_mouse_events)
    mouse_thread.daemon = True
    mouse_thread.start()
    
    mouse.hook(on_mouse_click)

    def listen_for_commands():
        while True:
            try:
                command = input()
                if command == "DISCONNECT":
                    client_socket.send("DISCONNECT".encode())
                    break
            except Exception as e:
                pass  

    command_thread = threading.Thread(target=listen_for_commands)
    command_thread.daemon = True
    command_thread.start()

    try:
        keyboard.wait('esc')  
    except KeyboardInterrupt:
        pass
    finally:
        keyboard.unhook_all()
        mouse.unhook_all()
        if not client_socket._closed:
            client_socket.close()
        print("Connection closed.")
        
def receive_screen_data(host, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    
    root = tk.Tk()
    root.title("Remote Screen")

    canvas = tk.Canvas(root)
    canvas.pack(fill=tk.BOTH, expand=True)

    photo = None

    def update_image(image_data):
        nonlocal photo
        try:
            # טעינת התמונה מהבייטים שהתקבלו
            image = Image.open(io.BytesIO(image_data))
            
            # שינוי גודל התמונה כך שתתאים לגבולות המקסימליים
            max_width = 1920  # התאמה לפי הצורך
            max_height = 1080 # התאמה לפי הצורך
            image.thumbnail((max_width, max_height), Image.ANTIALIAS)
            
            # שינוי גודל הקנבס כך שיתאים לגודל התמונה
            width, height = image.size
            canvas.config(width=width, height=height)
            
            # המרה ל-PhotoImage
            photo = ImageTk.PhotoImage(image)
            
            # עדכון הקנבס עם התמונה החדשה
            canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            root.update_idletasks()
            root.update()
            
            # הדפסת מידע נוסף לצורכי דיבאג
            print("Image updated successfully.")
        except Exception as e:
            print(f"Error updating image: {e}")

    try:
        while True:
            # קריאת גודל נתוני התמונה (שימו לב שמתקבל כבתים)
            image_size_data = client_socket.recv(1024)
            if not image_size_data:
                print("Connection closed by the server.")
                break

            # ניסיון לפענח את גודל התמונה
            try:
                image_size = int(image_size_data.decode())
            except ValueError:
                print(f"Received non-integer data: {image_size_data}")
                continue
            
            image_data = b''
            while len(image_data) < image_size:
                packet = client_socket.recv(image_size - len(image_data))
                if not packet:
                    break
                image_data += packet
            
            # דיבאג: הדפסת גודל התמונה שהתקבלה
            print(f"Received image size: {len(image_data)}")
            
            # עדכון התמונה בקנבס
            update_image(image_data)

    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        client_socket.close()
        root.destroy()

# פונקציה עיקרית להפעלת הקוד במחשב השולט
def main():
    host = input("Enter the IP address of the controlled computer: ").strip()
    actions_port = 12346
    screen_port = 12345

    # הרצת פונקציות קבלת המסך ושליחת הפעולות במקביל
    screen_thread = threading.Thread(target=receive_screen_data, args=(host, screen_port))
    actions_thread = threading.Thread(target=send_actions, args=(host, actions_port))

    screen_thread.daemon = True
    actions_thread.daemon = True

    screen_thread.start()
    actions_thread.start()

    screen_thread.join()
    actions_thread.join()

if __name__ == "__main__":
    main()
