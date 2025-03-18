// websocket.js
const webSocketUrl = 'ws://your-websocket-url';
let webSocket = null;

export const connectWebSocket = (onMessageCallback) => {
  if (webSocket) {
    console.warn('WebSocket уже подключен');
    return;
  }

  webSocket = new WebSocket(webSocketUrl);

  webSocket.onopen = () => {
    console.log('WebSocket соединение установлено');
  };

  webSocket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    onMessageCallback(message);
  };

  webSocket.onclose = () => {
    console.log('WebSocket соединение закрыто');
    webSocket = null; // Сбрасываем WebSocket при закрытии
  };

  webSocket.onerror = (error) => {
    console.error('Ошибка WebSocket:', error);
  };
};

export const sendMessage = (message) => {
  if (webSocket && webSocket.readyState === WebSocket.OPEN) {
    webSocket.send(JSON.stringify(message));
  } else {
    console.error('WebSocket не подключен');
  }
};

export const disconnectWebSocket = () => {
  if (webSocket) {
    webSocket.close();
  }
};
