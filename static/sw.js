// Service Worker for 色花堂智能助手 Pro
const CACHE_NAME = 'aw98tang-v1.1.0';
const STATIC_CACHE = 'aw98tang-static-v1.1';
const DYNAMIC_CACHE = 'aw98tang-dynamic-v1.1';

// 需要缓存的静态资源
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/offline.html',
  'https://unpkg.com/lucide@latest',
  'https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css'
];

// 安装 Service Worker
self.addEventListener('install', event => {
  console.log('🔧 Service Worker 安装中...');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('📦 缓存静态资源');
        // 不要因为个别资源失败而导致整个安装失败
        return Promise.allSettled(
          urlsToCache.map(url => 
            cache.add(url).catch(err => console.warn('缓存失败:', url))
          )
        );
      })
      .then(() => {
        console.log('✅ Service Worker 安装完成');
        return self.skipWaiting(); // 立即激活新 Service Worker
      })
  );
});

// 激活 Service Worker
self.addEventListener('activate', event => {
  console.log('✅ Service Worker 激活中...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          // 删除旧版本缓存
          if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
            console.log('🗑️ 删除旧缓存:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('✅ Service Worker 已激活');
      return self.clients.claim(); // 立即接管所有页面
    })
  );
});

// 拦截网络请求
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // 跳过 chrome-extension 和非 http(s) 协议
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // API 请求：网络优先策略
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          // 克隆响应用于缓存
          if (response && response.status === 200) {
            const responseClone = response.clone();
            caches.open(DYNAMIC_CACHE).then(cache => {
              cache.put(request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          // API 失败时尝试返回缓存
          return caches.match(request).then(cachedResponse => {
            if (cachedResponse) {
              console.log('📦 API 从缓存返回:', url.pathname);
              return cachedResponse;
            }
            // 返回离线 JSON 响应
            return new Response(JSON.stringify({
              success: false,
              message: '网络连接失败，请检查网络'
            }), {
              headers: { 'Content-Type': 'application/json' }
            });
          });
        })
    );
    return;
  }

  // 静态资源：缓存优先策略
  event.respondWith(
    caches.match(request)
      .then(cachedResponse => {
        if (cachedResponse) {
          console.log('📦 从缓存返回:', url.pathname);
          return cachedResponse;
        }

        // 缓存未命中，从网络获取
        return fetch(request).then(response => {
          // 只缓存成功的 GET 请求
          if (!response || response.status !== 200 || request.method !== 'GET') {
            return response;
          }

          // 克隆响应用于缓存
          const responseToCache = response.clone();
          caches.open(DYNAMIC_CACHE).then(cache => {
            cache.put(request, responseToCache);
          });

          return response;
        });
      })
      .catch(() => {
        // 离线时返回离线页面
        if (request.mode === 'navigate') {
          return caches.match('/offline.html').then(response => {
            return response || new Response('离线模式', {
              headers: { 'Content-Type': 'text/html; charset=utf-8' }
            });
          });
        }
      })
  );
});

// 后台同步
self.addEventListener('sync', event => {
  console.log('🔄 后台同步触发:', event.tag);
  
  if (event.tag === 'sync-stats') {
    event.waitUntil(syncStats());
  }
});

// 同步统计数据
async function syncStats() {
  try {
    const response = await fetch('/api/stats');
    if (response.ok) {
      const data = await response.json();
      console.log('✅ 统计数据同步成功', data);
      
      // 通知所有客户端
      const clients = await self.clients.matchAll();
      clients.forEach(client => {
        client.postMessage({
          type: 'STATS_SYNCED',
          data: data
        });
      });
    }
  } catch (error) {
    console.error('❌ 统计数据同步失败:', error);
    throw error; // 让浏览器稍后重试
  }
}

// 推送通知（可选功能）
self.addEventListener('push', event => {
  console.log('📬 收到推送通知');
  
  const data = event.data ? event.data.json() : {};
  const title = data.title || '色花堂智能助手';
  const options = {
    body: data.body || '有新的通知',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/icon-72x72.png',
    vibrate: [200, 100, 200],
    tag: data.tag || 'notification',
    requireInteraction: false,
    data: {
      dateOfArrival: Date.now(),
      url: data.url || '/'
    },
    actions: [
      {
        action: 'open',
        title: '查看详情'
      },
      {
        action: 'close',
        title: '关闭'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// 通知点击事件
self.addEventListener('notificationclick', event => {
  console.log('🔔 通知被点击:', event.action);
  event.notification.close();

  if (event.action === 'open') {
    const urlToOpen = event.notification.data.url || '/';
    event.waitUntil(
      clients.matchAll({ type: 'window', includeUncontrolled: true })
        .then(windowClients => {
          // 查找已打开的窗口
          for (let client of windowClients) {
            if (client.url === urlToOpen && 'focus' in client) {
              return client.focus();
            }
          }
          // 打开新窗口
          if (clients.openWindow) {
            return clients.openWindow(urlToOpen);
          }
        })
    );
  }
});

// 消息通信
self.addEventListener('message', event => {
  console.log('📨 收到消息:', event.data);
  
  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data.type === 'CACHE_URLS') {
    event.waitUntil(
      caches.open(DYNAMIC_CACHE).then(cache => {
        return cache.addAll(event.data.urls);
      })
    );
  }
  
  if (event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => caches.delete(cacheName))
        );
      }).then(() => {
        event.ports[0].postMessage({ success: true });
      })
    );
  }
});

// 定期清理过期缓存（可选）
self.addEventListener('periodicsync', event => {
  if (event.tag === 'clear-old-cache') {
    event.waitUntil(clearOldCache());
  }
});

async function clearOldCache() {
  const cache = await caches.open(DYNAMIC_CACHE);
  const requests = await cache.keys();
  const now = Date.now();
  const maxAge = 7 * 24 * 60 * 60 * 1000; // 7天

  for (let request of requests) {
    const response = await cache.match(request);
    const dateHeader = response.headers.get('date');
    if (dateHeader) {
      const cacheTime = new Date(dateHeader).getTime();
      if (now - cacheTime > maxAge) {
        await cache.delete(request);
        console.log('🗑️ 清理过期缓存:', request.url);
      }
    }
  }
}

console.log('🌸 色花堂智能助手 Pro - Service Worker 已加载');

