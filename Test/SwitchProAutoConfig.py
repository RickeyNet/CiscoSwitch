import argparse
from jinja2 import Environment, FileSystemLoader
import csv, os

def generate_configs(template_name, input_file, output_dir):
    env = Environment(loader=FileSystemLoader('./templates'))
    template = env.get_template(template_name)
    os.makedirs(output_dir, exist_ok=True)

    with open(input_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            cfg = template.render(row)
            with open(f"{output_dir}/{row['hostname']}.cfg", 'w') as f:
                f.write(cfg)
    print(f"✅ All configs generated in {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cisco Config Generator")
    parser.add_argument("--template", required=True, help="Template filename (e.g., access_switch.j2)")
    parser.add_argument("--input", required=True, help="CSV file with switch data")
    parser.add_argument("--output", default="./output", help="Output directory")
    args = parser.parse_args()
    generate_configs(args.template, args.input, args.output)
