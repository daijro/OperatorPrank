<h1 align="center">
    OperatorPrank
</h1>


<p align="center">
    <a href="https://github.com/daijro/OperatorPrank/blob/main/LICENSE">
        <img src="https://img.shields.io/github/license/daijro/OperatorPrank">
    </a>
    <a href="https://python.org/">
        <img src="https://img.shields.io/badge/python-3.10-blue">
    </a>
    <a href="https://github.com/ambv/black">
        <img src="https://img.shields.io/badge/code%20style-black-black.svg">
    </a>
    <a href="https://github.com/PyCQA/isort">
        <img src="https://img.shields.io/badge/imports-isort-black.svg">
    </a>
</p>


<h5 align="center">
    Simple CLI tool to route two phones to each other
</h5>


## How It Works

This tool generates free accounts on "prank dial" website(s). The result is that the two phones will be connected to each other, and each phone will think that the other phone is calling it.

## Usage

1. Run `python main.py` and wait for an account to generate.
2. Select "Operator" to route two phones to each other, or an audio playback prank.
3. Enter two phone numbers (formatting doesn't matter). If "Operator" was selected, the two numbers will "call" each other. If an audio recording was selected, the "Dest" number will recieve the phone call from the "Spoof" number.
4. Wait for the call to finish. It will now return a recording of the call.

https://github.com/daijro/OperatorPrank/assets/72637910/ebba8f10-aa3a-4baa-a3c2-39912e1bbac8


## Disclaimer

This repository is _not_ associated with or endorsed by providers of the APIs contained in this GitHub repository. This project is intended **for educational purposes only**. It is strictly intended to demonstrate the use of proxy rotators in Python networking.

The API used in this repository belong to its respective owner. This project is _not_ claiming any right over them nor is it affiliated with or endorsed by any of the providers mentioned.
