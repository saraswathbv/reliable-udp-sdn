# Reliable UDP File Transfer Using SDN

## Overview
This project aims to implement reliable file transfer over UDP with Software-Defined Networking (SDN).

The application layer handles reliable delivery using sequence numbers, acknowledgements, timeouts, retransmissions, and checksum validation.

The SDN component uses an OpenFlow controller and Mininet to manage and test network forwarding.

## Technologies
- C / UDP sockets
- Python
- OS-Ken SDN controller
- OpenFlow 1.3
- Mininet
- Open vSwitch

## SDN Component
The SDN controller communicates with OpenFlow switches and manages packet forwarding. Mininet is used to emulate the network topology and test connectivity.

## Current Progress
- [x] Installed Mininet and Open vSwitch.
- [x] Installed OS-Ken.
- [x] Created an OpenFlow controller.
- [x] Successfully tested basic two-host connectivity.
- [ ] Implement alternative network paths.
- [ ] Test network link failures and path changes.
- [ ] Integrate and test reliable UDP file transfer.

## Requirements
- Ubuntu Linux
- Python 3.12
- Mininet
- Open vSwitch
- OS-Ken 3.1.1

## Running the SDN Controller
Activate the Python environment:

    source .venv312/bin/activate

Start the controller:

    osken-manager controller.py --ofp-tcp-listen-port 6653

Keep the controller running while testing Mininet in another terminal.

## Basic Network Test
In a second terminal, run:

    sudo mn -c

Then start Mininet:

    sudo mn --topo single,2 --controller remote,ip=127.0.0.1,port=6653 --switch ovsk,protocols=OpenFlow13

At the Mininet prompt, run:

    pingall

A successful test should report 0% packet loss.

## Project Status
The basic two-host connectivity test has worked previously. Alternative-path routing, link-failure testing, and integration with the reliable UDP application remain to be completed.
