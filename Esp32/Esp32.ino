#include <DHT.h>
#include <WiFi.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include <utility>

class Sensor_DHT22 {
public:
  static Sensor_DHT22 *getInstance(const uint8_t pin) {
    if (instance == nullptr) {
      instance = new Sensor_DHT22(pin);
      instance->setup();
    }
    return instance;
  }

  static void destroyInstance() {
    delete instance;
    instance = nullptr;
  }

  const float readHumidity() {
    // 减少延时，避免阻塞系统
    delay(20);
    return dht.readHumidity();
  }

  const float readTemperature() {
    // 减少延时，避免阻塞系统
    delay(20);
    return dht.readTemperature();
  }

  const std::pair<float, float> get_temperature_humidity() {
    // 减少延时，避免阻塞系统
    delay(20);
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();
    return std::make_pair(temperature, humidity);
  }

private:
  explicit Sensor_DHT22(const uint8_t pin)
    : pin(pin),
      dht(pin, DHT22) {
  }

  Sensor_DHT22(const Sensor_DHT22 &) = delete;
  Sensor_DHT22 &operator=(const Sensor_DHT22 &) = delete;
  ~Sensor_DHT22() {
  }

private:
  void setup() {
    // 只初始化一次串口
    if (!Serial) {
      Serial.begin(115200);
    }
    dht.begin();
  }

private:
  uint8_t pin;
  DHT dht;
  static Sensor_DHT22 *instance;
};

Sensor_DHT22 *Sensor_DHT22::instance = nullptr;

class Websocket_manager {
public:
  void cleanupClients() {
    // 清理断开的客户端
    ws.cleanupClients();
  }

  static Websocket_manager *getInstance(const String &ssid, const String &password,
                                        const String &url, const uint16_t port, const uint8_t pin_DHT22) {
    if (instance == nullptr) {
      instance = new Websocket_manager(ssid, password, url, port, pin_DHT22);
      instance->setup();
    }
    return instance;
  }

  static void destroyInstance() {
    if (instance) {
      instance->disconnectAllClients();
      instance->dht22->destroyInstance();
      delete instance;
      instance = nullptr;
    }
  }

  // 主动断开所有客户端连接
  void disconnectAllClients() {
    ws.closeAll();
    // 给客户端一些时间处理断开
    delay(100);
  }

private:
  explicit Websocket_manager(const String &ssid, const String &password,
                             const String &url, const uint16_t port, const uint8_t pin_DHT22)
    : ssid(ssid), password(password), url(url), port(port),
      server(port), ws(url) {
    dht22 = Sensor_DHT22::getInstance(pin_DHT22);
  }

  Websocket_manager(const Websocket_manager &) = delete;
  Websocket_manager &operator=(const Websocket_manager &) = delete;

  ~Websocket_manager() {
    // 确保在销毁前断开所有连接
    disconnectAllClients();
    server.end();
  }

  void setup() {
    // 只初始化一次串口
    if (!Serial) {
      Serial.begin(115200);
    }

    Serial.print("Connecting to ");
    Serial.println(ssid);

    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
    }

    Serial.println("");
    Serial.println("Connected..!");
    Serial.print("Got IP: ");
    Serial.println(WiFi.localIP());

    ws.onEvent(event_handler_static);
    server.addHandler(&ws);
    server.begin();
  }

  static void handle_websocket_message(AsyncWebSocket *server, AsyncWebSocketClient *client, void *arg, uint8_t *data, size_t len) {
    // 检查实例是否存在
    if (instance == nullptr || client == nullptr) return;

    // 检查客户端是否有效
    if (!client->canSend()) {
      Serial.printf("Client #%u is not ready to send data\n", client->id());
      return;
    }

    AwsFrameInfo *info = (AwsFrameInfo *)arg;
    if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT) {
      // 确保字符串有终止符
      if (len < 255) {
        data[len] = 0;
      } else {
        data[254] = 0;
      }

      StaticJsonDocument<256> doc;
      DeserializationError error = deserializeJson(doc, data);

      if (error) {
        Serial.print("JSON parsing failed: ");
        Serial.println(error.c_str());
        return;
      }

      const char *from = doc["from"] | "";
      if (strcmp(from, "AI_server") == 0) {
        const char *type = doc["type"] | "";
        if (strcmp(type, "humidity_temperature") == 0) {
          std::pair<float, float> th = instance->dht22->get_temperature_humidity();
          DynamicJsonDocument doc_resp(512);  // 使用动态文档避免堆栈溢出
          doc_resp["from"] = "esp32_sensors";
          doc_resp["to"] = "AI_server";
          doc_resp["id"] = doc["id"].as<int>();
          doc_resp["type"] = "humidity_temperature";
          doc_resp["temperature"] = th.first;
          doc_resp["humidity"] = th.second;

          // 使用动态缓冲区
          char *output = (char *)malloc(512);
          if (output) {
            serializeJson(doc_resp, output, 512);
            instance->ws.text(client->id(), output);
            free(output);
          } else {
            Serial.println("Memory allocation failed for JSON response");
          }
        }
      }
    }
  }

  static void event_handler_static(AsyncWebSocket *server, AsyncWebSocketClient *client,
                                   AwsEventType type, void *arg, uint8_t *data, size_t len) {
    if (client == nullptr) return;

    switch (type) {
      case WS_EVT_CONNECT:
        Serial.printf("WebSocket client #%u connected from %s\n", client->id(), client->remoteIP().toString().c_str());
        break;

      case WS_EVT_DISCONNECT:
        Serial.printf("WebSocket client #%u disconnected\n", client->id());
        // 这里可以添加客户端断开后的清理操作
        break;

      case WS_EVT_DATA:
        handle_websocket_message(server, client, arg, data, len);
        break;

      case WS_EVT_PONG:
        Serial.printf("WebSocket client #%u pong received\n", client->id());
        break;

      case WS_EVT_ERROR:
        Serial.printf("WebSocket client #%u error: %s\n", client->id(), (char *)data);
        // 发生错误时可以主动断开客户端
        if (client->canSend()) {
          client->close();
        }
        break;
    }
  }

private:
  String ssid;
  String password;
  String url;
  uint16_t port;
  AsyncWebServer server;
  AsyncWebSocket ws;
  Sensor_DHT22 *dht22;
  static Websocket_manager *instance;
};

Websocket_manager *Websocket_manager::instance = nullptr;

Websocket_manager *websocket_manager;
// 示例使用方法
uint8_t Sensor_HC_SR501_pin = 26;
bool led_state = 0;
const uint8_t led_pin = 2;

void setup() {
  pinMode(led_pin, OUTPUT);
  pinMode(Sensor_HC_SR501_pin, INPUT);
  digitalWrite(led_pin, LOW);

  const char *ssid = "403";
  const char *password = "14031403";

  // 创建单例实例
  websocket_manager = Websocket_manager::getInstance(ssid, password, "/ws", 80, 4);
}

// 在程序结束时调用
void end() {
  // 确保安全销毁实例
  if (websocket_manager) {
    Websocket_manager::destroyInstance();
    websocket_manager = nullptr;
  }
}

void loop() {
  // 定期清理断开的客户端
  websocket_manager->cleanupClients();

  // 添加一些非阻塞延时，让系统有时间处理其他任务
  delay(10);
}