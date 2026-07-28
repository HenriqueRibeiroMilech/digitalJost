
import oracledb
import pandas as pd
import urllib
import subprocess
import platform
import re
import sys

from sqlalchemy import create_engine, text

from app.utils.constants import CNNX_JDT


def ping_ip(ip_address, count=4):
    """
    Pings an IP address and returns the result
    
    Args:
        ip_address (str): The IP address to ping
        count (int): Number of ping requests to send (default: 4)
        
    Returns:
        dict: Dictionary containing ping results including:
            - success (bool): Whether the ping was successful
            - sent (int): Number of packets sent
            - received (int): Number of packets received
            - loss (float): Packet loss percentage
            - min_time (float): Minimum round trip time in ms
            - avg_time (float): Average round trip time in ms
            - max_time (float): Maximum round trip time in ms
            - output (str): Raw output from the ping command
    """
    # Determine the OS to format the ping command properly
    current_os = platform.system().lower()
    
    # Initialize the result dictionary
    result = {
        'success': False,
        'sent': 0,
        'received': 0,
        'loss': 100.0,
        'min_time': None,
        'avg_time': None,
        'max_time': None,
        'output': ""
    }
    
    try:
        if current_os == 'windows':
            # Windows ping command
            command = ['ping', '-n', str(count), ip_address]
        else:
            # Linux/Unix ping command
            command = ['ping', '-c', str(count), ip_address]
        
        # Execute the ping command
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        
        # Store the raw output
        result['output'] = stdout
        
        # Check if the ping was successful (exit code 0)
        if process.returncode == 0:
            result['success'] = True
            
            # Parse the output to extract metrics
            if current_os == 'windows':
                # Windows output parsing
                sent_match = re.search(r'Sent = (\d+)', stdout)
                received_match = re.search(r'Received = (\d+)', stdout)
                loss_match = re.search(r'Lost = (\d+) \((\d+)% loss\)', stdout)
                times_match = re.search(r'Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms', stdout)
                
                if sent_match and received_match:
                    result['sent'] = int(sent_match.group(1))
                    result['received'] = int(received_match.group(1))
                
                if loss_match:
                    result['loss'] = float(loss_match.group(2))
                
                if times_match:
                    result['min_time'] = float(times_match.group(1))
                    result['max_time'] = float(times_match.group(2))
                    result['avg_time'] = float(times_match.group(3))
            else:
                # Linux/Unix output parsing
                sent_received_match = re.search(r'(\d+) packets transmitted, (\d+) received', stdout)
                loss_match = re.search(r'(\d+(?:\.\d+)?)% packet loss', stdout)
                times_match = re.search(r'min/avg/max(?:/mdev)? = (\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)', stdout)
                
                if sent_received_match:
                    result['sent'] = int(sent_received_match.group(1))
                    result['received'] = int(sent_received_match.group(2))
                
                if loss_match:
                    result['loss'] = float(loss_match.group(1))
                
                if times_match:
                    result['min_time'] = float(times_match.group(1))
                    result['avg_time'] = float(times_match.group(2))
                    result['max_time'] = float(times_match.group(3))
    
    except Exception as e:
        result['output'] = f"Error executing ping: {str(e)}"
    
    return result


def test_ping(ip_address="8.8.8.8", logger=None):
    """
    Test function to ping an IP address and log the results
    
    Args:
        ip_address (str): The IP address to ping (default: 8.8.8.8 - Google DNS)
        logger (Logger): Optional logger object. If provided, results are logged instead of printed
    """
    log_or_print = logger.info if logger else print
    
    log_or_print(f"Pinging {ip_address}...")
    result = ping_ip(ip_address)
    
    message = f"\nPing Results for {ip_address}:\n"
    message += f"Success: {'Yes' if result['success'] else 'No'}\n"
    message += f"Packets: Sent={result['sent']}, Received={result['received']}, Loss={result['loss']}%\n"
    
    if result['min_time'] is not None:
        message += f"Round Trip Times: Min={result['min_time']}ms, Avg={result['avg_time']}ms, Max={result['max_time']}ms\n"
    
    message += "\nRaw Output:\n"
    message += result['output']
    
    log_or_print(message)
    
    return result


def default(logger):
    test_ping("10.1.32.160", logger)  # Example: Test ping to your router
    
    