#!/usr/bin/python3
"""
Analyze collected MQTT experiment data
"""
import csv
import sys
from collections import defaultdict
from datetime import datetime

def analyze_mqtt_log(filename):
    print("\n" + "=" * 70)
    print(f"MQTT EXPERIMENT ANALYSIS: {filename}")
    print("=" * 70 + "\n")
    
    messages_by_sensor = defaultdict(int)
    messages_by_type = defaultdict(int)
    timestamps = []
    
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
        if not rows:
            print("No data found in file!")
            return
        
        for row in rows:
            sensor_id = row['Sensor_ID']
            metric_type = row['Metric_Type']
            elapsed = float(row['Elapsed_Seconds'])
            
            messages_by_sensor[sensor_id] += 1
            messages_by_type[metric_type] += 1
            timestamps.append(elapsed)
    
    total_messages = len(timestamps)
    duration = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
    
    # Overall Statistics
    print("OVERALL STATISTICS")
    print("-" * 70)
    print(f"  Total Messages:     {total_messages}")
    print(f"  Experiment Duration: {duration:.1f} seconds")
    if duration > 0:
        print(f"  Average Rate:        {total_messages/duration:.2f} messages/second")
    print()
    
    # Messages by Sensor
    print("MESSAGES BY SENSOR")
    print("-" * 70)
    for sensor, count in sorted(messages_by_sensor.items()):
        percentage = (count / total_messages * 100) if total_messages > 0 else 0
        print(f"  {sensor:<15} {count:>6} messages  ({percentage:>5.1f}%)")
    print()
    
    # Messages by Type
    print("MESSAGES BY TYPE")
    print("-" * 70)
    for metric, count in sorted(messages_by_type.items()):
        percentage = (count / total_messages * 100) if total_messages > 0 else 0
        print(f"  {metric:<15} {count:>6} messages  ({percentage:>5.1f}%)")
    print()
    
    # Time-based Analysis
    if len(timestamps) > 1:
        print("TIME-BASED ANALYSIS")
        print("-" * 70)
        
        # Calculate intervals between messages
        intervals = []
        sorted_times = sorted(timestamps)
        for i in range(1, len(sorted_times)):
            intervals.append(sorted_times[i] - sorted_times[i-1])
        
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            min_interval = min(intervals)
            max_interval = max(intervals)
            
            print(f"  Average interval:    {avg_interval:.3f} seconds")
            print(f"  Minimum interval:    {min_interval:.3f} seconds")
            print(f"  Maximum interval:    {max_interval:.3f} seconds")
        print()
    
    print("=" * 70 + "\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_data.py <csv_file>")
        print("\nExample:")
        print("  python3 analyze_data.py mqtt_data_experiment1.csv")
        sys.exit(1)
    
    analyze_mqtt_log(sys.argv[1])
