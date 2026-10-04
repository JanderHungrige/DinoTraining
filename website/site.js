/* Doc 133: language, the latest release (latest.json, written by the server's updater),
   and the copy buttons. No framework, no third-party requests. */
(function () {
  'use strict';

  var DE = {
    'nav.repo': 'Quellcode',
    'hero.title': 'Ein Bildmodell anlernen, mit ein paar hundert Bildern.',
    'hero.lead':
      'V-Rex (Vision Representation & Experimentation) ist eine kostenlose Desktop-App für den ganzen Ablauf: Bilder mit Grounding DINO und SAM annotieren, kleine Heads auf eingefrorenen DINOv2/DINOv3-Backbones in Minuten trainieren, sie anwenden und neue Daten von ihnen annotieren lassen.',
    'release.loading': 'Neueste Version wird gesucht…',
    'release.none': 'Die erste Version erscheint in Kürze',
    'release.version': 'Version {version} · {date}',
    'dl.title': 'Download',
    'dl.soon': 'Erste Version folgt',
    'dl.windows': 'Für Windows laden ({size})',
    'dl.linux': '.deb laden ({size})',
    'win.meta': 'Windows 10/11, 64 Bit',
    'win.store': 'Im Microsoft Store holen',
    'win.storeNote': 'Von Microsoft signiert, ohne Warnung, und es aktualisiert sich selbst.',
    'win.or': 'Oder direkt der Installer:',
    'win.note':
      'Der Installer ist nicht mit einem kostenpflichtigen Zertifikat signiert, deshalb warnt Windows einmal mit SmartScreen: <em>Weitere Informationen → Trotzdem ausführen</em>. Keine Admin-Rechte nötig.',
    'mac.meta': 'Apple Silicon (M1 und neuer)',
    'mac.step': '<em>Terminal</em> öffnen und einfügen:',
    'mac.note':
      'Installiert in deinen Programme-Ordner, ohne Admin-Rechte und ohne Sicherheitswarnung. Nicht über den Browser: macOS blockiert unsignierte Apps, die ein Browser geladen hat. Zum Aktualisieren einfach erneut ausführen. Intel-Macs werden nicht unterstützt (PyTorch gibt es für sie nicht mehr).',
    'linux.meta': 'Ubuntu / Debian, x86-64',
    'linux.step': 'Dann im Download-Ordner:',
    'cmd.copy': 'Kopieren',
    'cmd.copied': 'Kopiert',
    'fact.first.title': 'Der erste Start',
    'fact.first.text':
      'Die Installer sind klein (etwa 35–45 MB, das meiste davon die bewegten Hintergründe). Beim ersten Start lädt die App einmal Python und PyTorch von den offiziellen Quellen, genau in den getesteten Versionen: etwa 1 GB, mit NVIDIA-GPU-Unterstützung etwa 3,5 GB. Danach funktioniert sie offline.',
    'fact.gpu.title': 'Deine GPU',
    'fact.gpu.text':
      'NVIDIA-Karten werden erkannt und über CUDA genutzt, Apple Silicon über MPS. Ohne GPU läuft die App auf der CPU; umschalten kannst du später in der App.',
    'fact.open.title': 'Open Source',
    'fact.open.text':
      'MIT-lizenziert. Modelle lädt die App von Hugging Face; deine Bilder und Datensätze bleiben auf deinem Rechner oder in dem Cloud-Speicher, den du selbst verbindest. Keine Telemetrie.',
    'more.releases': 'Alle Versionen und Prüfsummen',
    'more.repo': 'Der Code auf GitHub',
    'more.source': 'Deinstallieren und aus dem Quellcode bauen',
    'more.privacy': 'Datenschutz',
    'foot.video': 'Hintergrund: Waldvideo von Pexels (Pexels-Lizenz).'
  };

  var EN = {
    'release.none': 'The first release is coming soon',
    'release.version': 'Version {version} · {date}',
    'dl.windows': 'Download for Windows ({size})',
    'dl.linux': 'Download .deb ({size})',
    'cmd.copied': 'Copied'
  };

  var nodes = Array.prototype.slice.call(document.querySelectorAll('[data-i18n]'));
  // English is the page itself: remember it before any switch.
  nodes.forEach(function (node) {
    var key = node.getAttribute('data-i18n');
    if (!(key in EN)) EN[key] = node.innerHTML.trim();
  });

  var lang = 'en';
  var release = null;

  function text(key, params) {
    var value = (lang === 'de' ? DE[key] : undefined) || EN[key] || key;
    Object.keys(params || {}).forEach(function (name) {
      value = value.split('{' + name + '}').join(params[name]);
    });
    return value;
  }

  function mb(bytes) {
    return Math.round(bytes / (1024 * 1024)) + ' MB';
  }

  function render() {
    document.documentElement.lang = lang;
    document.getElementById('lang').textContent = lang === 'de' ? 'EN' : 'DE';
    nodes.forEach(function (node) {
      node.innerHTML = text(node.getAttribute('data-i18n'));
    });
    var version = document.getElementById('version');
    if (release === null) {
      version.innerHTML = text('release.loading');
      return;
    }
    if (!release.version) {
      version.textContent = text('release.none');
      return;
    }
    var date = new Date(release.published_at).toLocaleDateString(lang === 'de' ? 'de-DE' : 'en-GB', {
      year: 'numeric', month: 'long', day: 'numeric'
    });
    version.textContent = text('release.version', { version: release.version, date: date });
    button('dl-windows', release.assets.windows, 'dl.windows');
    button('dl-linux', release.assets.linux, 'dl.linux');
    document.getElementById('all-releases').href = release.html_url;
  }

  function button(id, asset, key) {
    var link = document.getElementById(id);
    if (!asset) return;
    link.href = asset.url;
    link.textContent = text(key, { size: mb(asset.size) });
    link.removeAttribute('data-i18n');
  }

  function choose(next) {
    lang = next;
    try {
      localStorage.setItem('dinotraining.site.lang', lang);
    } catch (error) {
      /* private mode: the choice lasts this page view */
    }
    render();
  }

  var stored = null;
  try {
    stored = localStorage.getItem('dinotraining.site.lang');
  } catch (error) {
    stored = null;
  }
  lang = stored || ((navigator.language || 'en').toLowerCase().indexOf('de') === 0 ? 'de' : 'en');
  document.getElementById('lang').addEventListener('click', function () {
    choose(lang === 'de' ? 'en' : 'de');
  });

  document.querySelectorAll('[data-copy]').forEach(function (copy) {
    copy.addEventListener('click', function () {
      var command = document.getElementById(copy.getAttribute('data-copy')).textContent;
      var done = function () {
        copy.textContent = text('cmd.copied');
        setTimeout(function () { copy.textContent = text('cmd.copy'); }, 1600);
      };
      if (navigator.clipboard) {
        navigator.clipboard.writeText(command).then(done, function () { /* left selectable */ });
      }
    });
  });

  render();
  fetch('latest.json', { cache: 'no-cache' })
    .then(function (response) { return response.ok ? response.json() : { version: null }; })
    .catch(function () { return { version: null }; })
    .then(function (data) {
      release = data;
      render();
    });
})();
