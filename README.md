# Asset tracking with Pycom devices, Sigfox and Google Cloud

This solution tutorial demonstrates how to use a Pycom device, the Sigfox network,
and Google Cloud to track the position of physical assets.

Please refer to [this article](https://cloud.google.com/solutions/tracking-assets-with-iot-devices-pycom-sigfox-gcp) for the steps to run the code.

## Contents of this repository

- CLI interface of the parser and source of the Cloud Function to decode payloads coming from the Pycom device.
- BigQuery schema for sensor and positioning data.
- MicroPython application that sends sensor and positioninig data and messages using the Sigfox radio network.
