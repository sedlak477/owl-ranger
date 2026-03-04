import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def process_csv(filepath):
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return
        
    if 'angle' not in df.columns or 'measured_angle' not in df.columns:
        print(f"Skipping {filepath}, missing 'angle' or 'measured_angle' columns.")
        return
        
    angle = df['angle']
    measured = df['measured_angle']
    
    # Calculate error in radians
    error = measured - angle
    # Handle angle wrapping (-pi to pi)
    error = (error + np.pi) % (2 * np.pi) - np.pi
    abs_error = np.abs(error)
    
    # Convert to degrees for better visualization
    angle_deg = np.degrees(angle)
    abs_error_deg = np.degrees(abs_error)
    
    plt.figure(figsize=(10, 6))
    plt.scatter(angle_deg, abs_error_deg, alpha=0.5, marker='.')
    plt.xlabel('Angle (degrees)')
    plt.ylabel('Absolute Angle Error (degrees)')
    plt.title(f'Absolute Angle Error vs Angle\n{filepath.name}')
    plt.grid(True)
    plt.tight_layout()
    
    # Save plot as PNG alongside the CSV file
    out_path = filepath.with_suffix('.png')
    plt.savefig(out_path)
    plt.close()
    print(f"Saved plot to {out_path}")

def main():
    # Process all CSV files in the 'out' directory
    out_dir = Path("out")
    if not out_dir.exists():
        print("Directory 'out' not found.")
        return
        
    csv_files = list(out_dir.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {out_dir}")
        return
        
    for csv_file in csv_files:
        process_csv(csv_file)

if __name__ == "__main__":
    main()
