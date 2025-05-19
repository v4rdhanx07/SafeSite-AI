# ESP32-CAM PPE Detection via Streamlit

A real-time dashboard for monitoring Personal Protective Equipment (PPE) compliance using an ESP32-CAM and Streamlit. The app displays live detection results, triggers alerts for missing PPE or unauthorized personnel, and supports email notifications and alert history.

## Features

- Live PPE detection dashboard (Helmet, Goggle, Vest, Unauthorized Labourer)
- Real-time serial data from ESP32-CAM
- Email and in-app alerts for missing PPE or unauthorized labourers
- Alert cooldown and customizable thresholds
- Alert history stored in SQLite database
- Buzzer sound for critical alerts

## Requirements

- Python 3.7+
- ESP32-CAM sending detection results over serial (USB)
- [Streamlit](https://streamlit.io/)
- [pyserial](https://pyserial.readthedocs.io/)
- [playsound](https://github.com/TaylorSMarks/playsound)
- [altair](https://altair-viz.github.io/)
- [pandas](https://pandas.pydata.org/)

## Installation

```sh
pip install streamlit pyserial playsound altair pandas
```

## Configuration

1. **Serial Port:**  
   Change the COM port in [`app.py`](app.py) (default is `COM3`) to match your ESP32-CAM's port.

2. **Email Alerts:**  
   Set up your email credentials in [`.streamlit/secrets.toml`](.streamlit/secrets.toml):

   ```toml
   EMAIL_HOST = "smtp.gmail.com"
   EMAIL_PORT = 587
   EMAIL_USER = "your_email@gmail.com"
   EMAIL_PASS = "your_app_password"
   ```

3. **Buzzer Sound:**  
   Ensure `siren-alert-96052.mp3` exists at the specified path or update `BUZZER_SOUND` in [`app.py`](app.py).

## Usage

1. Connect your ESP32-CAM and ensure it is sending detection results over serial.
2. Run the Streamlit app:

   ```sh
   streamlit run app.py
   ```

3. A browser window will open showing live PPE detection results.
4. Use the sidebar to configure alert settings and view alert history.

## Files

- [`app.py`](app.py): Main Streamlit application.
- [`alerts.db`](alerts.db): SQLite database for alert history.
- [`siren-alert-96052.mp3`](siren-alert-96052.mp3): Buzzer sound file.
- [`.streamlit/secrets.toml`](.streamlit/secrets.toml): Email credentials (not tracked by git).
- [`README.md`](README.md): This documentation.

## Notes

- For Gmail, you may need to use an App Password if 2FA is enabled.
- The app is designed for Windows (`COM3`); update the serial port for other OSes.
- All alert history is stored locally in `alerts.db`.

## License

MIT License
