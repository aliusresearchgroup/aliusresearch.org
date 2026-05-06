# Newsletter FormBee Setup

The newsletter page posts both forms through FormBee. The site code keeps Discord webhook URLs out of the browser.

Discord webhook URLs are secrets. Do not paste them into `Newsletter/page.html`, generated files under `docs/`, or any committed JavaScript. If a webhook URL was shared in a chat or issue, rotate it in Discord before using it for production.

## Hosted FormBee

Hosted FormBee is the simplest setup if the free plan includes the Discord integration for your account. The site can safely expose a FormBee API key as long as the form is restricted to `aliusresearch.org` in FormBee's allowed-domain settings; the Discord webhook URL stays inside FormBee.

1. Create two FormBee forms:
   - `newsletterSignup`
   - `newsletterNews`
2. In FormBee, enable the Discord plugin for each form.
3. Paste the newsletter signup Discord webhook URL into the `newsletterSignup` FormBee Discord plugin.
4. Paste the news-item Discord webhook URL into the `newsletterNews` FormBee Discord plugin.
5. Replace the endpoints in `Newsletter/page.html`:

```html
<script>
  window.ALIUS_FORMBEE_ENDPOINTS = {
    newsletterSignup: 'https://api.formbee.dev/formbee/REPLACE_WITH_SIGNUP_API_KEY',
    newsletterNews: 'https://api.formbee.dev/formbee/REPLACE_WITH_NEWS_API_KEY'
  };
</script>
```

The site currently points both newsletter forms at the same hosted FormBee endpoint. If you want signup and news submissions to route through separate FormBee forms, create a second FormBee API key and replace one endpoint in `Newsletter/page.html`.

## Self-Hosted FormBee Webhooks

For a fully free software path, self-host FormBee's webhooks-only service. Run two FormBee webhook services so each form can reach a different Discord channel. Store the Discord URLs in environment variables, not in the repository. Hosting may still cost money depending on where you run the containers.

```powershell
$env:NEWSLETTER_SIGNUP_DISCORD_WEBHOOK = "https://discord.com/api/webhooks/..."
$env:NEWSLETTER_NEWS_DISCORD_WEBHOOK = "https://discord.com/api/webhooks/..."

docker run -e WEBHOOK_URL="$env:NEWSLETTER_SIGNUP_DISCORD_WEBHOOK" -e ORIGIN="https://aliusresearch.org" -p 3001:3000 oia123/formbee-webhooks
docker run -e WEBHOOK_URL="$env:NEWSLETTER_NEWS_DISCORD_WEBHOOK" -e ORIGIN="https://aliusresearch.org" -p 3002:3000 oia123/formbee-webhooks
```

Then expose those services with a reverse proxy:

- `https://aliusresearch.org/webhook/newsletter-signup` -> signup FormBee service `/webhook/send`
- `https://aliusresearch.org/webhook/newsletter-news-item` -> news-item FormBee service `/webhook/send`

GitHub Pages can serve the newsletter page, but it cannot safely store Discord webhook secrets or run the FormBee backend. The webhook forwarding service needs to live on a host such as Railway, Fly.io, Render, a VPS, or another container-capable service, then be routed from the public endpoint above.
