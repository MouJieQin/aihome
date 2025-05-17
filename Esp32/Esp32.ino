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
    delay(2000);
    return dht.readHumidity();
  }
  const float readTemperature() {
    delay(2000);
    return dht.readTemperature();
  }

  const std::pair<float, float> get_temperature_humidity() {
    delay(2000);
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
    Serial.begin(115200);
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
    instance->dht22->destroyInstance();
    delete instance;
    instance = nullptr;
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
    server.end();
    ws.closeAll();
  }

  void setup() {
    Serial.begin(115200);

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
    if (instance == nullptr) return;

    AwsFrameInfo *info = (AwsFrameInfo *)arg;
    if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT) {
      data[len] = 0;
      StaticJsonDocument<200> doc;
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
          JsonDocument doc_resp;
          doc_resp["from"] = "esp32_sensors";
          doc_resp["to"] = "AI_server";
          doc_resp["id"] = doc["id"];
          doc_resp["type"] = "humidity_temperature";
          doc_resp["temperature"] = th.first;
          doc_resp["humidity"] = th.second;
          char output[256];
          serializeJson(doc_resp, output);
          instance->ws.text(client->id(), output);
        }
      }
    }
  }

  static void event_handler_static(AsyncWebSocket *server, AsyncWebSocketClient *client,
                                   AwsEventType type, void *arg, uint8_t *data, size_t len) {
    switch (type) {
      case WS_EVT_CONNECT:
        Serial.printf("WebSocket client #%u connected from %s\n", client->id(), client->remoteIP().toString().c_str());
        break;
      case WS_EVT_DISCONNECT:
        Serial.printf("WebSocket client #%u disconnected\n", client->id());
        break;
      case WS_EVT_DATA:
        handle_websocket_message(server, client, arg, data, len);
        break;
      case WS_EVT_PONG:
      case WS_EVT_ERROR:
        Serial.printf("WebSocket client #%u WS_EVT_ERROR or WS_EVT_PONG\n", client->id());
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
  Websocket_manager::destroyInstance();
}

void loop() {
  // if (digitalRead(Sensor_HC_SR501_pin) == HIGH) {
  //   if (led_state == LOW) {
  //     Serial.println("Sensor_HC_SR501_pin is Activated.");
  //     led_state = HIGH;
  //     digitalWrite(led_pin, led_state);
  //   } else {
  //   }
  // } else {
  //   if (led_state == LOW) {
  //   } else {
  //     Serial.println("Sensor_HC_SR501_pin is Deactivated.");
  //     led_state = LOW;
  //     digitalWrite(led_pin, led_state);
  //   }
  // }
  websocket_manager->cleanupClients();
  // delay(1000);
}
