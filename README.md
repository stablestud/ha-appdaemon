# Personal Home Assistant automations

Automations (apps) are bound with AppDaemon which does the talking to HA

```
uv python install cpython-3.9.21-linux-x86_64-gnu
source ./.venv/bin/activate*
uv sync
appdaemon -c $(pwd)
```

## Secrets

Secrets are stored in `secrets.yaml`

It can be securely backed up into `rclone` cloud storage.
For example:
```
rclone copy ./secrets.yaml secrets:appdaemon/
```
