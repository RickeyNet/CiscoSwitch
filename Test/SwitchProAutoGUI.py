# -----------------------------
# Cisco Config Generator (GUI)
# -----------------------------

# Import required libraries
import PySimpleGUI as sg           # For building the graphical user interface
from jinja2 import Environment, FileSystemLoader  # For template rendering
import csv                         # To read CSV input files with switch data
import os                          # To handle file paths and create directories

# -----------------------------
# Function to generate configs
# -----------------------------
def generate_configs(template_name, input_file, output_dir):
    """
    Reads a Jinja2 template and a CSV file with switch data,
    renders the template for each switch, and saves the configs.
    
    Args:
        template_name (str): Path to the Jinja2 template file.
        input_file (str): Path to the CSV file containing switch info.
        output_dir (str): Folder where generated configs will be saved.
    """
    # Create a Jinja2 environment that knows where to find templates
    env = Environment(loader=FileSystemLoader('./templates'))
    
    # Load the specific template file
    template = env.get_template(template_name)
    
    # Ensure the output directory exists; create it if it doesn't
    os.makedirs(output_dir, exist_ok=True)
    
    # Open the CSV file and read each row as a dictionary
    with open(input_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Render the template using values from the current row
            cfg = template.render(row)
            
            # Save the rendered config to a file named after the switch hostname
            with open(f"{output_dir}/{row['hostname']}.cfg", 'w') as f:
                f.write(cfg)
    
    # Popup message to indicate success
    sg.popup("✅ Success", f"Configs saved in {output_dir}")

# -----------------------------
# Build the GUI Layout
# -----------------------------
layout = [
    # Row 1: Template file selection
    [sg.Text("Template:"), sg.Input(key="TEMPLATE"), sg.FileBrowse()],
    
    # Row 2: CSV file selection
    [sg.Text("Data File:"), sg.Input(key="CSV"), sg.FileBrowse()],
    
    # Row 3: Output folder selection
    [sg.Text("Output Folder:"), sg.Input(key="OUT"), sg.FolderBrowse()],
    
    # Row 4: Buttons
    [sg.Button("Generate Configs"), sg.Button("Exit")]
]

# -----------------------------
# Create the GUI Window
# -----------------------------
window = sg.Window("Cisco Config Generator", layout)

# -----------------------------
# Event Loop to keep GUI running
# -----------------------------
while True:
    event, values = window.read()  # Wait for user interaction
    
    # Close the window if user clicks 'Exit' or closes window
    if event in (sg.WINDOW_CLOSED, "Exit"):
        break
    
    # When user clicks "Generate Configs"
    if event == "Generate Configs":
        # Call the function with the user's inputs
        generate_configs(values["TEMPLATE"], values["CSV"], values["OUT"])

# -----------------------------
# Close the GUI Window properly
# -----------------------------
window.close()
