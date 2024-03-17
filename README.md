# Personal Home Assistant automations

Automations (apps) are bound with AppDaemon which does the talking to HA

```
python3 -m venv .venv --prompt ha-appdaemon
source ./.venv/bin/activate*
pip install -r requirements.txt
appdaemon -c $(pwd)
```
