# PLC to VLC Controller

**Python TCP server controlling VLC media player via Siemens S7-1200 PLC.**

---

## Overview

This project demonstrates real-time control of VLC media player using a Siemens S7-1200 PLC via TCP communication.  
The Python server receives simple numeric commands from the PLC, executes VLC actions, and sends responses or heartbeat signals back.



**Features:**

- Start, Stop, Pause, Resume, Reset, Rewind videos
- Thread-safe VLC control
- End-of-file notifications to PLC
- Heartbeat (livebit) communication
- Compatible with Windows VLC installation
- Auto reconnect on connection loss

## Command Mapping (PLC → VLC)

| Command | Action               |
|---------|----------------------|
| 1       | Start video          |
| 2       | Stop video           |
| 3       | Reset video          |
| 4       | Pause video          |
| 5       | Resume video         |
| 6       | Rewind to 0 sec      |
| 7       | Rewind to 5 sec      |
|---------|----------------------|

## Usage

1. Start Python server: `python serwer_TCP.py`
2. Connect your PLC to `HOST:PORT` (TCP)
3. Send command bytes from PLC (1=start, 2=stop, 3=reset, etc.)
4. Watch VLC respond in real-time
5. Monitor heartbeat messages and end-of-file notifications in the server console.

## Requirements
- Python 3.x
- python-vlc
- Siemens TIA Portal project for S7-1200

## File structure
- `python_server/` – Python script controlling VLC
- `plc_program/` – PLC project files


## Install python-vlc via pip:
```bash
pip install python-vlc
