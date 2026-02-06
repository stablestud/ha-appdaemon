# Personal Home Assistant automations

Automations (apps) are bound with AppDaemon which does the talking to HA

```
uv python install cpython-3.13.11-linux-x86_64-gnu
uv venv
source ./.venv/bin/activate
uv sync
appdaemon -c $(pwd)
```

## Updating packages
```
uv sync --upgrade
```

## Secrets

Secrets are stored in `secrets.yaml`

It can be securely backed up into `rclone` cloud storage.
For example:
```
rclone copy ./secrets.yaml secrets:appdaemon/
```

## Dev logs

You can make specific apps forward their logs to `./dev.log` by adding:
```
ha2mqtt:
  log: dev_log <-- Add this then the self.log() output of the app will be redirected; useful for developing
```
