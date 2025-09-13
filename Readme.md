# Buttplug Says!

This project is a "Simon Says" style game built in Python but with a little more fun~. It's designed to run on Windows and uses `tkinter` for the graphical user interface. The game presents a series of timed tasks to the user, who must perform the action if "Simon says" they should, or do nothing if Simon doesn't say, if they fail they will get punished.

### Features

* **Interactive GUI**: A simple, functional user interface created with `tkinter`.

* **Dynamic Tasks**: Tasks are loaded from a configurable `tasks.json` file, allowing you to easily add or change tasks. The game can tell you to open a link, post on Bluesky, or other actions.

* **Windows Integration**: The application uses `pygetwindow` to check if specific windows are open, verifying task completion.

* **Bluesky Integration**: Includes the ability to verify if a post has been successfully made on Bluesky.

### Haptic Feedback with Buttplug.io

This game integrates with the incredible **buttplug.io** platform to provide haptic feedback. By connecting to a Buttplug server, the application can control compatible devices. Vibration intensity is used to communicate with the player, with stronger feedback for success and a different sensation for failure, making the game more immersive and engaging.

---

### Prerequisites

To run this application, you'll need to install the following Python packages:

* `buttplug-py`

* `pygetwindow`

* `requests`

* `pyperclip`

* `tkinter` (usually comes with Python)

You can install these dependencies using `pip`:

```

pip install buttplug-py pygetwindow requests pyperclip
```

You will also need to have a Buttplug server running in the background. You can download one from the [Buttplug.io](https://buttplug.io/) website.

### How to Run

1.  Clone this repository to your local machine.

2.  Install the required Python packages.

3.  Modify the `config.json` file to set up your Bluesky account details if you plan to use the Bluesky post verification task.

4.  Run the application from your terminal:

```

python main.py
```

### Project Files

* `main.py`: The main script that contains the core game logic, UI, and integration code.

* `tasks.json`: A JSON file that defines the tasks for the game. You can add or modify tasks here.

* `config.json`: A JSON file for application-specific settings, such as Bluesky account information.

* `BebasNeue-Regular.ttf`: The font file for the "Simon Says!" title in the UI.

### Credits

* **Google Fonts**: The title font **Bebas Neue** was sourced from [Google Fonts](https://fonts.google.com/specimen/Bebas+Neue).
```