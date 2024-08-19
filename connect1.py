import socket
import pyautogui
import io
import time
import threading
import keyboard

# פונקציה לשליחת נתוני מסך למחשב השולט
def send_screen_data(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(1)
    
    print(f"Listening on port {port} for screen data...")
    client_socket, _ = server_socket.accept()
    print("Connected to the controlling computer")

    try:
        while True:
            # צילום מסך
            screenshot = pyautogui.screenshot()
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # שליחת גודל התמונה ונתוני התמונה
            img_size = len(img_byte_arr)
            client_socket.sendall(f"{img_size:<10}".encode())
            client_socket.sendall(img_byte_arr)
            print(f"Sent image of size: {img_size}")
            time.sleep(1)
    finally:
        client_socket.close()
        server_socket.close()

# פונקציה לקבלת פעולות עכבר ומקלדת מהמחשב השולט
def receive_actions(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(1)
    print(f"Listening on port {port} for actions...")

    client_socket, client_address = server_socket.accept()
    print(f"Connected to {client_address}")

    def process_action(action):
        parts = action.split(':')
        if len(parts) < 2:
            print("Malformed action received.")
            return

        if parts[0] == "KEY":
            key = parts[1]
            keyboard.press_and_release(key)
        elif parts[0] == "MOUSE":
            if parts[1] == "MOVE":
                x, y = map(int, parts[2].split(','))
                pyautogui.moveTo(x, y)
            elif parts[1] == "CLICK":
                button = parts[2].strip()
                pyautogui.click(button=button)

    try:
        while True:
            action = client_socket.recv(1024).decode().strip()
            if not action:
                print("Connection closed by the client.")
                break
            if action == "DISCONNECT":
                print("Disconnect signal received.")
                break
            try:
                process_action(action)
            except (ValueError, IndexError) as e:
                print(f"Error processing action: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")
                break
    except KeyboardInterrupt:
        print("Server interrupted.")
    finally:
        client_socket.close()
        server_socket.close()
        print("Connection closed.")

# פונקציה עיקרית להפעלת הקוד במחשב הנשלט
def main():
    screen_port = 12345
    actions_port = 12346

    # הרצת שתי הפונקציות במקביל עם פורטים שונים
    screen_thread = threading.Thread(target=send_screen_data, args=(screen_port,))
    actions_thread = threading.Thread(target=receive_actions, args=(actions_port,))

    screen_thread.daemon = True
    actions_thread.daemon = True

    screen_thread.start()
    actions_thread.start()

    screen_thread.join()
    actions_thread.join()

if __name__ == "__main__":
    main()
