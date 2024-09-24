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

![img_1.png](img_1.png)

![img.png](img.png)

Payloads are stored in the root of agent folder

Agent requires installation of `python3` and some dependencies. It can be installed by using the following:

- Linux: `sudo apt-get install python`
- Windows: https://www.python.org/downloads/

- Install dependencies:
`pip3 install rich pyyaml mutidict cryptography marshmallow marshmallow-enum`

# Running script

- Instruction for running: `python calderalone.py --help`
```
usage: calderalone.py [-h] [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [-O {plain-text,base64,base64jumble,caesar cipher,base64noPadding}] [-P {windows,linux}] [-E EXECUTORS]


 ██████╗ █████╗ ██╗     ██████╗ ███████╗██████╗  █████╗
██╔════╝██╔══██╗██║     ██╔══██╗██╔════╝██╔══██╗██╔══██╗
██║     ███████║██║     ██║  ██║█████╗  ██████╔╝███████║
██║     ██╔══██║██║     ██║  ██║██╔══╝  ██╔══██╗██╔══██║
╚██████╗██║  ██║███████╗██████╔╝███████╗██║  ██║██║  ██║
 ╚═════╝╚═╝  ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝


options:
  -h, --help            show this help message and exit
  -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --log {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set the logging level
  -O {plain-text,base64,base64jumble,caesar cipher,base64noPadding}, --obfuscate {plain-text,base64,base64jumble,caesar cipher,base64noPadding}
                        Set the obfuscator
  -P {windows,linux}, --platform {windows,linux}
                        Set executing platform
  -E EXECUTORS, --executors EXECUTORS
                        Set executors

```
- Running: `python calderalone.py -l DEBUG -P windows -E "psh, cmd" -O base64`