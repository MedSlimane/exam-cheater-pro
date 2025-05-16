import pyperclip
# import keyboard # Unused, replaced by pynput
import time
import requests
import threading
import logging
from pynput import keyboard as pynput_keyboard
# import os # Unused
import platform
import sys
import math  # For tray icon animations
from PIL import Image, ImageDraw # For placeholder icon
from pystray import MenuItem as item, Icon as icon

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ollama_clipboard_assistant.log"),
        logging.StreamHandler()
    ]
)

# Global instances for easier access in shared functions
assistant_instance = None
tray_icon_instance = None
assistant_thread_instance = None

# Application states for icon display
APP_STATE_IDLE = "idle"
APP_STATE_PROCESSING = "processing"
APP_STATE_ERROR = "error"
current_app_state = APP_STATE_IDLE

class OllamaClipboardAssistant:
    def __init__(self, model="llama3", ollama_url="http://localhost:11434"):
        self.model = model
        self.ollama_url = ollama_url
        self.previous_clipboard = ""
        self.is_processing = False
        self.running = False # Start as not running; set to True by start_listening
        self.modifier_pressed = False
        self.ctrl_pressed = False
        self.listener = None # pynput listener instance
        
        self.system = platform.system()
        if self.system == "Darwin":
            self.modifier_key = pynput_keyboard.Key.cmd
        else:
            self.modifier_key = pynput_keyboard.Key.ctrl
            
        logging.info(f"Ollama Clipboard Assistant initialized with model: {model}")
        logging.info(f"Running on: {self.system}")
        
    def check_ollama_availability(self):
        """Check if Ollama server is running and responsive"""
        global current_app_state
        
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5) # Added timeout
            if response.status_code == 200:
                logging.info("Successfully connected to Ollama server")
                # Update tray icon to idle state if it was previously in error state
                if current_app_state == APP_STATE_ERROR:
                    update_tray_icon(APP_STATE_IDLE)
                return True
        except requests.exceptions.RequestException:
            logging.error(f"Could not connect to Ollama server at {self.ollama_url}")
            # Update tray icon to show error state
            update_tray_icon(APP_STATE_ERROR)
            # No need to return False here, as it's the default path
        return False # Explicitly return False if not successful or exception
            
    def query_ollama(self, prompt):
        """Send a query to Ollama API and return the response"""
        try:
            logging.info(f"Sending request to Ollama with model: {self.model}")
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=60  # Add a timeout to prevent hanging indefinitely
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "No response from model")
            else:
                logging.error(f"Error from Ollama API: {response.status_code} - {response.text}")
                return f"Error: Could not get response from Ollama (Status code: {response.status_code})"
        except requests.exceptions.RequestException as e:
            logging.error(f"Request to Ollama failed: {str(e)}")
            return "Error: Failed to connect to Ollama service"
            
    def on_key_press(self, key):
        """Monitor for modifier key presses."""
        try:
            if key == self.modifier_key: # For Cmd+C (macOS) or Ctrl+C (Win/Linux)
                self.modifier_pressed = True
            if key == pynput_keyboard.Key.ctrl: # Specifically for Ctrl+Esc exit shortcut
                self.ctrl_pressed = True
        except AttributeError:
            # Some keys might not have all attributes (e.g., media keys)
            pass
            
    def on_key_release(self, key):
        global assistant_instance, tray_icon_instance # Access globals
        try:
            # Check for copy shortcut (Cmd+C or Ctrl+C)
            if getattr(key, 'char', None) == 'c' and self.modifier_pressed and not self.is_processing:
                shortcut_name = "Cmd+C" if self.system == "Darwin" else "Ctrl+C"
                logging.info(f"{shortcut_name} detected. Processing clipboard.")
                threading.Timer(0.1, self.process_clipboard).start()

            # Check for Ctrl+Esc exit shortcut
            if key == pynput_keyboard.Key.esc and self.ctrl_pressed:
                logging.info("Exit shortcut (Ctrl+Esc) detected. Requesting shutdown...")
                if tray_icon_instance and assistant_instance: # Ensure instances exist
                    perform_exit(tray_icon_instance, assistant_instance) 
                # self.running is set to False by perform_exit via stop_listening()
                # The 'if not self.running: return False' below will handle stopping the listener.

            # Update modifier states on release
            if key == self.modifier_key:
                self.modifier_pressed = False
            if key == pynput_keyboard.Key.ctrl:
                self.ctrl_pressed = False
                
        except AttributeError:
            pass
        
        # If self.running became False (e.g., by Ctrl+Esc or tray exit), ensure listener stops.
        if not self.running:
            return False # Stop the pynput listener callback chain
        return True # Continue listener otherwise
            
    def process_clipboard(self):
        """Process clipboard content with Ollama"""
        global current_app_state
        
        if self.is_processing:
            return
            
        self.is_processing = True
        try:
            # Get clipboard content
            current_clipboard = pyperclip.paste()
            
            # Check if clipboard has changed
            if current_clipboard != self.previous_clipboard and current_clipboard.strip():
                logging.info("New clipboard content detected")
                self.previous_clipboard = current_clipboard
                
                # Update tray icon to show processing state
                update_tray_icon(APP_STATE_PROCESSING)
                
                # Process with Ollama
                try:
                    response = self.query_ollama(current_clipboard)
                    
                    # Update clipboard with response
                    pyperclip.copy(response)
                    logging.info("Clipboard updated with Ollama response")
                    
                    # Update tray icon back to idle state
                    update_tray_icon(APP_STATE_IDLE)
                except Exception as e:
                    logging.error(f"Error during Ollama processing: {str(e)}")
                    # Update tray icon to error state
                    update_tray_icon(APP_STATE_ERROR)
                    # After a brief delay, return to idle state
                    threading.Timer(3.0, lambda: update_tray_icon(APP_STATE_IDLE)).start()
        except Exception as e:
            logging.error(f"Error processing clipboard: {str(e)}")
            update_tray_icon(APP_STATE_ERROR)
            # After a brief delay, return to idle state
            threading.Timer(3.0, lambda: update_tray_icon(APP_STATE_IDLE)).start()
        finally:
            self.is_processing = False
            
    def start_listening(self):
        """Starts the clipboard monitoring and Ollama interaction."""
        if not self.check_ollama_availability():
            logging.error("Ollama server is not available. Clipboard monitoring will not start.")
            self.running = False 
            # Optionally: update tray icon to show error status if tray is already running
            return False # Indicate failure to start

        self.running = True
        self.modifier_pressed = False # Reset state
        self.ctrl_pressed = False    # Reset state
        logging.info("Starting clipboard monitoring...")
        
        # Set up key listener
        # Ensure listener is only created if not already existing or if previous one was stopped
        if not self.listener or not self.listener.is_alive():
            self.listener = pynput_keyboard.Listener(
                on_press=self.on_key_press,
                on_release=self.on_key_release
            )
            self.listener.start()
            logging.info("Clipboard listener started.")
        return True # Indicate success

    def stop_listening(self):
        """Stops the clipboard monitoring."""
        logging.info("Attempting to stop clipboard assistant...")
        self.running = False # Signal to stop processing and for on_key_release
        
        if self.listener:
            logging.info("Stopping pynput listener...")
            # pynput's stop() can be called from a different thread.
            # It signals the listener thread to terminate.
            self.listener.stop() 
            # It's good practice to join the listener thread if it was managed directly,
            # but pynput handles its own thread management internally.
            # We just need to ensure it's told to stop.
            self.listener = None # Clear the listener instance
            logging.info("Pynput listener has been signaled to stop.")
        else:
            logging.info("No active listener to stop.")
        logging.info("Ollama Clipboard Assistant has been stopped.")

# --- System Tray Specific Functions ---

def create_icon_image(state=APP_STATE_IDLE):
    """Creates a PIL Image for the tray icon based on the current application state.
    
    Args:
        state: The current application state (idle, processing, error)
    
    Returns:
        A PIL Image object representing the icon
    """
    width = 64
    height = 64
    
    # Define colors for different states
    if state == APP_STATE_IDLE:
        # Normal state - Dark grey background, light grey foreground
        color_bg = (50, 50, 50)
        color_fg = (200, 200, 200)
        text = "OCA"
    elif state == APP_STATE_PROCESSING:
        # Processing state - Blue background, white foreground
        color_bg = (0, 100, 200)
        color_fg = (255, 255, 255)
        text = "..."
    elif state == APP_STATE_ERROR:
        # Error state - Red background, white foreground
        color_bg = (200, 50, 50)
        color_fg = (255, 255, 255)
        text = "ERR"
    else:
        # Default/fallback - Grey
        color_bg = (100, 100, 100)
        color_fg = (200, 200, 200)
        text = "OCA"
    
    image = Image.new("RGB", (width, height), color_bg)
    dc = ImageDraw.Draw(image)
    
    # For processing state, draw an animated-like icon (rotating dots)
    if state == APP_STATE_PROCESSING:
        # Draw three dots in a circular pattern to suggest loading
        radius = min(width, height) // 4
        center_x, center_y = width // 2, height // 2
        dot_radius = radius // 3
        
        # Get current time for simple animation effect
        # time is already imported at the top of the file
        t = int(time.time() * 2) % 3  # Changes every 0.5 seconds, 3 positions
        
        # Draw dots with one highlighted based on time
        for i in range(3):
            angle = (i * 120 + 90) * (3.14159 / 180)  # Convert to radians
            x = center_x + int(radius * 0.7 * math.cos(angle))
            y = center_y + int(radius * 0.7 * math.sin(angle))
            
            # Highlight one dot based on time
            if i == t:
                dot_color = color_fg
            else:
                # Make other dots slightly dimmer
                r, g, b = color_fg
                dot_color = (r//2, g//2, b//2)
                
            dc.ellipse((x-dot_radius, y-dot_radius, x+dot_radius, y+dot_radius), fill=dot_color)
        
        return image
    
    # For other states, draw text
    try:
        from PIL import ImageFont
        # math is already imported at the top of the file
        
        font_size = 20
        try:
            # Attempt to load a common system font, fallback to default
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", font_size) # Common on Linux
            except IOError:
                font = ImageFont.load_default() # PIL's built-in default

        # Calculate text bounding box for centering
        # For Pillow versions >= 10.0.0, textbbox is preferred over textsize
        if hasattr(dc, 'textbbox'):
            bbox = dc.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else: # Fallback for older Pillow versions
            text_width, text_height = dc.textsize(text, font=font)

        text_x = (width - text_width) / 2
        text_y = (height - text_height) / 2
        dc.text((text_x, text_y), text, font=font, fill=color_fg)
        
    except Exception as e:
        logging.error(f"Error creating icon text: {e}")
        # Fallback: Draw a simple shape if text rendering fails
        if state == APP_STATE_PROCESSING:
            # Draw a circle to indicate processing
            dc.ellipse([(width//4, height//4), (width*3//4, height*3//4)], outline=color_fg, width=2)
        elif state == APP_STATE_ERROR:
            # Draw an X to indicate error
            dc.line([(width//4, height//4), (width*3//4, height*3//4)], fill=color_fg, width=3)
            dc.line([(width*3//4, height//4), (width//4, height*3//4)], fill=color_fg, width=3)
        else:
            # Draw a square for idle/default
            dc.rectangle([(width//4, height//4), (width*3//4, height*3//4)], fill=color_fg)
    
    return image

def update_tray_icon(state):
    """Updates the system tray icon to reflect the current application state.
    
    Args:
        state: The current application state (idle, processing, error)
    """
    global tray_icon_instance, current_app_state
    
    # Update the global state tracker
    current_app_state = state
    
    if tray_icon_instance:
        try:
            new_icon = create_icon_image(state)
            tray_icon_instance.icon = new_icon
            logging.info(f"Updated tray icon to {state} state")
        except Exception as e:
            logging.error(f"Failed to update tray icon: {e}")
    else:
        logging.warning("Cannot update tray icon: tray_icon_instance is None")

def perform_exit(icon_to_stop, assistant_to_stop):
    """Centralized function to handle application exit."""
    logging.info("Perform_exit called. Shutting down application...")
    if assistant_to_stop:
        assistant_to_stop.stop_listening() # This sets assistant_to_stop.running to False
    
    # Wait a brief moment for the listener thread to process the stop signal
    # This is particularly important if on_key_release might still be executing
    time.sleep(0.2) 

    if icon_to_stop:
        icon_to_stop.stop() # This will break the tray_icon.run() loop
    
    # The main thread (running tray_icon.run()) will then exit,
    # and the assistant_thread (if daemon) will be terminated.

def main():
    global assistant_instance, tray_icon_instance, assistant_thread_instance, current_app_state

    # Configure logging if not already configured (e.g., if run as __main__)
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("ollama_clipboard_assistant.log"),
                logging.StreamHandler(sys.stdout) # Log to console for easier debugging
            ]
        )

    model = "deepseek-r1:8b"  # Default model
    if len(sys.argv) > 1:
        model = sys.argv[1]
    
    assistant_instance = OllamaClipboardAssistant(model=model)
    
    logging.info(f"Ollama Clipboard Assistant attempting to start with model: {model}")
    logging.info("Application will run in the system tray.")
    logging.info("Right-click the tray icon for options or press Ctrl+Esc to exit.")

    # Attempt to start the assistant's listening logic in a separate thread
    # This thread will handle keyboard events and Ollama interaction.
    # It's crucial that start_listening checks for Ollama availability.
    
    assistant_thread_instance = threading.Thread(target=assistant_instance.start_listening, daemon=True)
    assistant_thread_instance.start()
    
    # Give a moment for the thread to start and for check_ollama_availability to run.
    time.sleep(1) 
    
    # Start with IDLE, but may change to ERROR below
    current_state = APP_STATE_IDLE
    
    if not assistant_instance.running:
        logging.error("Assistant failed to start (e.g., Ollama server unavailable or other issue).")
        logging.error("The application will attempt to run the tray icon, but core functionality might be disabled.")
        # Set the app state to error since Ollama is not available
        current_state = APP_STATE_ERROR
        current_app_state = APP_STATE_ERROR  # Update the global state
        # For now, let the tray icon run so the user can at least exit it.

    # Create the initial icon based on current state
    image = create_icon_image(current_state) 
    menu = (item('Exit', lambda: perform_exit(tray_icon_instance, assistant_instance)),)
    
    tray_icon_instance = icon("OllamaClipboardAssistant", image, "Ollama Assistant", menu)
    
    logging.info("Starting system tray icon...")
    try:
        # tray_icon_instance.run() is a blocking call.
        # It runs the pystray event loop in the main thread.
        tray_icon_instance.run() 
    except Exception as e:
        logging.error(f"Error running tray icon: {e}")
    finally:
        logging.info("Tray icon run loop has exited or an error occurred. Cleaning up...")
        # Ensure assistant is stopped and thread is handled, even if perform_exit wasn't called
        # or if tray_icon.run() exited unexpectedly.
        if assistant_instance and assistant_instance.running:
            logging.info("Ensuring assistant is stopped post-tray exit.")
            assistant_instance.stop_listening() 
        
        if assistant_thread_instance and assistant_thread_instance.is_alive():
            logging.info("Waiting for assistant thread to join...")
            assistant_thread_instance.join(timeout=5) # Wait for thread to finish
            if assistant_thread_instance.is_alive():
                logging.warning("Assistant thread did not terminate cleanly after join attempt.")
        
        logging.info("Application shutdown process complete.")

if __name__ == "__main__":
    main()

