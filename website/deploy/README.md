# The download site (doc 133)

Served at dino.w3rth.de (port 8002) and dino.questenterprise.de (port 8003) on
159.195.148.193, behind Nginx Proxy Manager. Everything lives in `~/dinotraining-site` of
the user `jan`; nothing in `/opt`, nothing as root.

## Setting it up once (as jan on the server)

```bash
mkdir -p ~/dinotraining-site/deploy
curl -fsSL https://raw.githubusercontent.com/JanderHungrige/DinoTraining/main/website/deploy/update-site.sh -o ~/dinotraining-site/deploy/update-site.sh
chmod +x ~/dinotraining-site/deploy/update-site.sh
~/dinotraining-site/deploy/update-site.sh
(crontab -l 2>/dev/null; echo '*/10 * * * * $HOME/dinotraining-site/deploy/update-site.sh >> $HOME/dinotraining-site/update.log 2>&1') | crontab -
```

The first run fetches the site and starts the container `dinotraining-site`.

## After that

- **Every 10 minutes** the script checks `main` (`dev` until main carries `website/`) and
  GitHub's latest release. A new commit is deployed in one switch; a new release updates
  `latest.json`, which the page reads for its download buttons.
- **Releases** come from `release.yml`: a merge to main with a new version in
  `apps/desktop/src-tauri/tauri.conf.json` publishes `v<version>` once all three
  installers have passed their smoke test.
- **Log:** `~/dinotraining-site/update.log`. **Stop:** `docker compose -p dinotraining-site
  down` and remove the crontab line.
