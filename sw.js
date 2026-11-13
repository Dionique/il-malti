/* Service worker: приложение работает без интернета.
 *
 * При установке в кэш кладётся всё, что нужно странице: стили, скрипт, файлы
 * данных, манифест и иконки. Дальше запросы отдаются из кэша, поэтому
 * приложение открывается и без сети. Имя кэша содержит версию сборки
 * (её подставляет bin/build), поэтому новая версия заменяет старую.
 *
 * Файл обязан лежать в корне сайта: от его расположения зависит область
 * действия (scope), а она должна накрывать всё приложение.
 */

var BUILD = "__BUILD__";
var CACHE = "il-malti-" + BUILD;

var FILES = [
  "./",
  "index.html",
  "styles.css",
  "app.js",
  "manifest.webmanifest",
  "icon-192.png",
  "icon-512.png",
  "data/words.js",
  "data/sentences.js",
  "data/ipa.js",
  "data/links.js",
  "data/pairs.js",
  "data/forms.js",
  "data/blanks.js",
  "data/dialogues.js"
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE)
      .then(function (cache) { return cache.addAll(FILES); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys()
      .then(function (keys) {
        return Promise.all(keys.map(function (key) {
          return key === CACHE ? null : caches.delete(key);
        }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (event) {
  var request = event.request;
  if (request.method !== "GET") return;
  if (request.url.indexOf("http") !== 0) return;

  event.respondWith(
    caches.match(request, { ignoreSearch: true }).then(function (hit) {
      if (hit) return hit;
      return fetch(request).then(function (response) {
        // то, что запросили мимо списка (например, адрес со слэшем), тоже кэшируем
        if (response && response.status === 200 && response.type === "basic") {
          var copy = response.clone();
          caches.open(CACHE).then(function (cache) { cache.put(request, copy); });
        }
        return response;
      }).catch(function () {
        // без сети: отдаём страницу, приложение дальше работает из кэша
        return caches.match("index.html");
      });
    })
  );
});
