// Daily Math for Kids — Service Worker
// Handles background push notifications and caching

const CACHE = 'dmk-v1';

self.addEventListener('install', e => {
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(clients.claim());
});

// Handle push messages sent from the server (Web Push)
self.addEventListener('push', e => {
  const data = e.data ? e.data.json() : {};
  e.waitUntil(
    self.registration.showNotification(data.title || '🧮 Daily Math for Kids', {
      body: data.body || "Today's problems are ready — keep your streak alive! 🔥",
      icon: data.icon || '/favicon.ico',
      badge: data.badge || '/favicon.ico',
      tag: 'dmk-daily',
      renotify: true,
      data: { url: data.url || '/' },
    })
  );
});

// When user clicks the notification, open the site
self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const c of list) {
        if (c.url.includes(self.location.origin) && 'focus' in c) return c.focus();
      }
      return clients.openWindow(e.notification.data?.url || '/');
    })
  );
});

// Handle periodic background sync for daily reminder (Chromium only)
self.addEventListener('periodicsync', e => {
  if (e.tag === 'dmk-daily-reminder') {
    e.waitUntil(
      self.registration.showNotification('🧮 Daily Math for Kids', {
        body: "Don't forget your daily practice — keep your streak alive! 🔥",
        icon: '/favicon.ico',
        tag: 'dmk-daily',
        data: { url: '/' },
      })
    );
  }
});
