import pyperclip
import keyboard
import time
import requests
import threading
import logging
from pynput import keyboard as pynput_keyboard
import os
import platform
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ollama_clipboard_assistant.log"),
        logging.StreamHandler()
    ]
)

class OllamaClipboardAssistant:
    def __init__(self, model="llama3", ollama_url="http://localhost:11434"):
        self.model = model
        self.ollama_url = ollama_url
        self.previous_clipboard = ""
        self.is_processing = False
        self.running = True
        self.modifier_pressed = False  # Flag for Cmd/Ctrl in copy shortcut
        self.ctrl_pressed = False    # Flag for Ctrl in Ctrl+Esc exit shortcut
        
        # Determine the appropriate modifier key based on OS
        self.system = platform.system()
        if self.system == "Darwin":  # macOS
            self.modifier_key = pynput_keyboard.Key.cmd
        else:  # Windows/Linux
            self.modifier_key = pynput_keyboard.Key.ctrl
            
        logging.info(f"Ollama Clipboard Assistant initialized with model: {model}")
        
        logging.info(f"Running on: {self.system}")
        
    def check_ollama_availability(self):
        """Check if Ollama server is running and responsive"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                logging.info("Successfully connected to Ollama server")
                return True
        except requests.exceptions.RequestException:
            logging.error(f"Could not connect to Ollama server at {self.ollama_url}")
            return False
            
    def query_ollama(self, prompt):
        """Send a query to Ollama API and return the response"""
        try:
            logging.info(f"Sending request to Ollama with model: {self.model}")
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False}
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
        """Handle key release events for shortcuts."""
        try:
            # Check for copy shortcut (Cmd+C or Ctrl+C)
            # This relies on 'c' being released while the modifier is still pressed.
            if getattr(key, 'char', None) == 'c' and self.modifier_pressed and not self.is_processing:
                shortcut_name = "Cmd+C" if self.system == "Darwin" else "Ctrl+C"
                logging.info(f"{shortcut_name} detected. Processing clipboard.")
                # Wait a moment for the clipboard to be updated
                threading.Timer(0.1, self.process_clipboard).start()

            # Check for Ctrl+Esc exit shortcut
            # This needs to be checked based on the state of ctrl_pressed when Esc is released.
            if key == pynput_keyboard.Key.esc and self.ctrl_pressed:
                logging.info("Exit shortcut (Ctrl+Esc) detected. Shutting down...")
                self.running = False
                return False  # Stop the listener callback chain

            # Update modifier states on release
            if key == self.modifier_key:
                self.modifier_pressed = False
            if key == pynput_keyboard.Key.ctrl: # Handles release of Ctrl for the Ctrl+Esc combo
                self.ctrl_pressed = False
                
        except AttributeError:
            # Some keys might not have all attributes
            pass
        
        # If self.running became False (e.g., by Ctrl+Esc), ensure listener stops.
        if not self.running:
            return False
            
    def process_clipboard(self):
        """Process clipboard content with Ollama"""
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
                
                # Process with Ollama
                response = self.query_ollama(current_clipboard)
                
                # Update clipboard with response
                pyperclip.copy(response)
                logging.info("Clipboard updated with Ollama response")
        except Exception as e:
            logging.error(f"Error processing clipboard: {str(e)}")
        finally:
            self.is_processing = False
            
    def run(self):
        """Main method to run the assistant"""
        if not self.check_ollama_availability():
            logging.error("Ollama server is not available. Please start Ollama and try again.")
            return
            
        logging.info("Starting clipboard monitoring...")
        self.modifier_pressed = False
        
        # Set up key listener
        listener = pynput_keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        listener.start()
        
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            logging.info("Keyboard interrupt received. Shutting down...")
        finally:
            listener.stop()
            logging.info("Clipboard assistant stopped")

def main():
    # Get model name from command line arguments if provided
    model = "deepseek-r1:8b"  # Default model
    if len(sys.argv) > 1:
        model = sys.argv[1]
    
    assistant = OllamaClipboardAssistant(model=model)
    print(f"Ollama Clipboard Assistant started with model: {model}")
    print("Copy text with Cmd+C (Mac) or Ctrl+C (Windows/Linux) to process with Ollama")
    print("Press Ctrl+Esc to exit")
    
    assistant.run()

if __name__ == "__main__":
    main()
    
    