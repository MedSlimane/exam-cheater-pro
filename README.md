# Ollama Clipboard Assistant

This Python script monitors your clipboard for text copied using Cmd+C (Mac) or Ctrl+C (Windows/Linux). When new text is detected, it sends the text to an Ollama instance for processing and replaces the clipboard content with the Ollama model's response.

## Features

*   **Clipboard Monitoring**: Automatically detects text copied to the clipboard.
*   **Ollama Integration**: Sends clipboard content to a specified Ollama model.
*   **Automatic Response**: Replaces clipboard content with the Ollama model's response.
*   **Cross-Platform**: Works on macOS, Windows, and Linux.
*   **Configurable Model**: Specify the Ollama model to use via command-line argument.
*   **Status Logging**: Logs activity and errors to `ollama_clipboard_assistant.log`.
*   **System Tray Integration**: Runs quietly in your system tray.
*   **Visual State Indicators**: The tray icon changes to show the current state:
    *   **Idle (grey)**: Ready for input
    *   **Processing (blue with animated dots)**: Currently processing clipboard
    *   **Error (red)**: Error connecting to Ollama or processing clipboard
*   **Customizable Ollama URL**: The Ollama server URL can be changed in the script.

## Requirements

*   Python 3
*   An Ollama instance running and accessible. (Default: `http://localhost:11434`)
*   The Python packages listed in `requirements.txt`.

## Installation

1.  **Clone the repository (if applicable) or download the script.**
2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    If `requirements.txt` is not present, you can create it with the following content:
    ```
    pyperclip
    keyboard
    requests
    pynput
    ```
    And then run `pip install -r requirements.txt`.

3.  **Ensure Ollama is running.** You can download and run Ollama from [https://ollama.com/](https://ollama.com/). Make sure the desired model is pulled, e.g., `ollama pull llama3`.

## Usage

Run the script from your terminal:

```bash
python exam-cheater.py [model_name]
```

*   `[model_name]` (optional): The name of the Ollama model you want to use (e.g., `llama3`, `deepseek-r1:8b`). If not provided, it defaults to `deepseek-r1:8b`.

Once started:

1.  The script will confirm it has started and which model it's using.
2.  Copy any text using your system's copy command (Cmd+C on macOS, Ctrl+C on Windows/Linux).
3.  The script will send this text to Ollama.
4.  The response from Ollama will automatically replace the content of your clipboard.
5.  To exit the script, press `Ctrl+Esc`.

## Configuration

*   **Ollama Model**:
    *   Can be set via a command-line argument when running the script.
    *   The default model is `deepseek-r1:8b`. This can be changed in the `main()` function in `exam-cheater.py`.
*   **Ollama Server URL**:
    *   Defaults to `http://localhost:11434`.
    *   This can be changed by modifying the `ollama_url` parameter in the `OllamaClipboardAssistant` class constructor within the `exam-cheater.py` script.

## Logging

The script logs its operations and any errors to a file named `ollama_clipboard_assistant.log` in the same directory as the script. It also prints informational messages to the console.

## How it Works

The script uses the `pynput` library to listen for global keyboard events.
When the copy shortcut (Cmd+C or Ctrl+C, depending on the OS) is detected:
1. It waits briefly for the system to update the clipboard.
2. It reads the content from the clipboard using `pyperclip`.
3. If the content is new and not empty, it sends a request to the Ollama API's `/api/generate` endpoint with the clipboard text as the prompt.
4. The response from Ollama is then copied back to the clipboard using `pyperclip`.

The `Ctrl+Esc` key combination is used to gracefully shut down the script.

## Building an Executable

You can build a standalone executable using PyInstaller:

1. Install PyInstaller:

```bash
pip install pyinstaller
```

2. Create the executable:

```bash
pyinstaller --onefile --windowed --name "ExamCheaterPro" exam-cheater.py
```

The `--windowed` flag ensures no console window appears when running the executable.
The built executable will be in the `dist` folder.
