# Standalone Agent: Calder-alone

An agent that simulates the [Caldera](https://github.com/mitre/caldera) functionality in planning and execution 
test cases for an adversary plan in an isolated environment (no need to initiate C2 connections as Caldera)

# Installation

Using the Standalone plugin with Caldera to enable auto-generating standalone agent 

To run Caldera along with the Standalone plugin and generate a standalone agent:
1. Download Caldera as detailed in the [Installation Guide](https://github.com/mitre/Caldera)
2. Enable the Standalone plugin by adding `- standalone` to the list of enabled plugins in `conf/local.yml` or `conf/default.yml` (if running Caldera in insecure mode)
3. Start Caldera 
4. Using `standalone` plugin to choose adversary, planner and fact source before generating agent (in `.tar.gz` or `.zip` format)
5. Download agent

# Additional setup
When executing the agent, it must be confirmed that the folder tree is organized correctly. 

E.g.
```
├── app
│   ├── learning
│   │   ├── some .py files here...
│   ├── objects
│   │   ├── some .py files here...
│   ├── planners
│   │   ├── atomic.py 
│   │   ├── some .py files here...
│   ├── service
│   │   ├── some .py files here...
│   ├── utility
│   │   ├── some .py files here...
│   └── other .py files ...
├── calderalone.py
├── conf
├── data
│   ├── abilities
│   │   ├── collection
│   │   │   ├── 4e97e699-93d7-4040-b5a3-2e906a58199e.yml
│   │   │   ├── 6469befa-748a-4b9c-a96d-f191fde47d89.yml
│   │   │   └── ...
│   │   └── ...
│   ├── adversary.yml
│   ├── exfil
│   │   └── reports
│   │       └── event_logs
│   ├── planner.yml
│   ├── results
│   ├── source.yml
│   └── sources
├── plugins
└── requirements.txt
```
Payloads are stored in the root of agent folder

Agent requires installation of `python3` and some dependencies. It can be installed by using the following:

- Linux: `sudo apt-get install python`
- Windows: https://www.python.org/downloads/

- Install dependencies:
  + `pip3 install rich pyyaml multidict cryptography marshmallow marshmallow-enum colorama tqdm psutil`
  + Or `pip3 install -r requirements.txt`

# Running script

- Instruction for running: `python calderalone.py --help`
```
usage: calderalone.py [-h] [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [-o {plain-text,base64,base64jumble,caesar cipher,base64noPadding}] [-p {windows,linux}]
                      [-e EXECUTORS] [-c {y,n}] [-P {User,Elevated}]
                      
options:
  -h, --help            show this help message and exit
  -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --log {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the logging level
  -o {plain-text,base64,base64jumble,caesar cipher,base64noPadding}, --obfuscate {plain-text,base64,base64jumble,caesar cipher,base64noPadding}
                        Set the obfuscator
  -p {windows,linux}, --platform {windows,linux}
                        Inform platform
  -e EXECUTORS, --executors EXECUTORS
                        Inform available executors
  -c {y,n}, --cleanup {y,n}
                        Cleanup operations or not
  -P {User,Elevated}, --privilege {User,Elevated}
                        Current privilege of agent

```
- Running: `python calderalone.py -l DEBUG -p windows -e "psh, cmd" -o base64 -c y -P Elevated`