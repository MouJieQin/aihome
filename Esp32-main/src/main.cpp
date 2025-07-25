#include <DHT.h>
#include <WiFi.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <esp_task_wdt.h>
#include <utility>
#include "WZ.h"
#define WDT_TIMEOUT 5
// 调试开关
#define DEBUG_MODE true

// ESP32-S NodeMCU Board serial port information
/*
 * There are three serial ports on the ESP32 known as UART0, UART1 and UART2.
 *
 * UART0 (GPIO1 - TX0, GPIO3 - RX0) is used to communicate with the ESP32 for programming and during reset/boot.
 * UART1 (GPIO10 - TX1, GPIO9 - RX1) is unused and can be used for your projects. Some boards use this port for SPI Flash access though
 * UART2 (GPIO17 - TX2, GPIO16 - RX2) is unused and can be used for your projects.
 *
 */

// Sensor class for ZE08 CH2O sensor
class Sensor_ZE08_CH2O
{
public:
  // Get singleton instance
  static Sensor_ZE08_CH2O *getInstance(bool activeMode = true)
  {
    static Sensor_ZE08_CH2O instance(activeMode); // Use static local variable for thread-safe singleton
    return &instance;
  }

  // Set sensor to active mode
  void activeMode()
  {
    is_active_mode = true;
    wz.activeMode();
  }

  // Set sensor to passive mode
  void passiveMode()
  {
    is_active_mode = false;
    wz.passiveMode();
  }

  // Read CH2O data
  const std::pair<bool, const std::pair<uint16_t, float>> read()
  {
    if (!is_active_mode)
    {
      wz.requestRead();
    }
    const bool res = wz.read(hcho_data);
    if (res)
    {
      float ugm3 = ppb_to_mgm3(hcho_data.HCHO_PPB);
      return {true, {hcho_data.HCHO_PPB, ugm3}};
    }
    return {false, {0, 0}};
  }

  // Read CH2O data with timeout
  const std::pair<bool, const std::pair<uint16_t, float>> readUntil(uint16_t timeout = WZ::SINGLE_RESPONSE_TIME)
  {
    if (!is_active_mode)
    {
      wz.requestRead();
    }
    const bool res = wz.readUntil(hcho_data, timeout);
    if (res)
    {
      float ugm3 = ppb_to_mgm3(hcho_data.HCHO_PPB);
      return {true, {hcho_data.HCHO_PPB, ugm3}};
    }
    return {false, {0, 0}};
  }

private:
  // Convert ppb to mg/m³
  const float ppb_to_mgm3(const uint16_t ppb) const
  {
    return ppb * 0.00125;
  }

  // Private constructor
  explicit Sensor_ZE08_CH2O(const bool activeMode)
      : wz(Serial2), is_active_mode(activeMode)
  {
    if (!Serial2)
    {
      Serial2.begin(9600);
    }
    if (is_active_mode)
    {
      wz.activeMode();
    }
    else
    {
      wz.passiveMode();
    }
  }

  // Disable copy constructor and assignment operator
  Sensor_ZE08_CH2O(const Sensor_ZE08_CH2O &) = delete;
  Sensor_ZE08_CH2O &operator=(const Sensor_ZE08_CH2O &) = delete;
  ~Sensor_ZE08_CH2O()
  {
    Serial2.end();
  }

  WZ wz;
  WZ::DATA hcho_data;
  bool is_active_mode;
};

// Sensor class for DHT22 sensor
class Sensor_DHT22
{
public:
  // Get singleton instance
  static Sensor_DHT22 *getInstance(const uint8_t pin)
  {
    static Sensor_DHT22 instance(pin); // Use static local variable for thread-safe singleton
    instance.setup();
    return &instance;
  }

  // Read humidity
  const float readHumidity()
  {
    // Reduce delay to avoid blocking the system
    delay(20);
    return dht.readHumidity();
  }

  // Read temperature
  const float readTemperature()
  {
    // Reduce delay to avoid blocking the system
    delay(20);
    return dht.readTemperature();
  }

  // Get temperature and humidity
  const std::pair<float, float> get_temperature_humidity()
  {
    // Reduce delay to avoid blocking the system
    delay(20);
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();
    return {temperature, humidity};
  }

private:
  // Private constructor
  explicit Sensor_DHT22(const uint8_t pin)
      : pin(pin),
        dht(pin, DHT22)
  {
  }

  // Disable copy constructor and assignment operator
  Sensor_DHT22(const Sensor_DHT22 &) = delete;
  Sensor_DHT22 &operator=(const Sensor_DHT22 &) = delete;

  // Initialize sensor
  void setup()
  {
    // Initialize serial port only once
    if (!Serial)
    {
      Serial.begin(115200);
    }
    dht.begin();
  }

  uint8_t pin;
  DHT dht;
};

class NonblockingDelayer
{
public:
  explicit NonblockingDelayer() : lastUpdate(ULONG_MAX) {}

  bool is_expired_when_delay(const unsigned long ms)
  {
    if (lastUpdate == ULONG_MAX)
    {
      lastUpdate = millis();
      return false;
    }
    unsigned long currentMillis = millis();
    if (currentMillis - lastUpdate >= ms)
    {
      lastUpdate = currentMillis;
      return true;
    }
    return false;
  }

private:
  // Disable copy constructor and assignment operator
  NonblockingDelayer(const NonblockingDelayer &) = delete;
  NonblockingDelayer &operator=(const NonblockingDelayer &) = delete;

  unsigned long lastUpdate;
};

// Class to manage WebSocket and MQTT communication
class Websocket_manager
{
public:
  // Get singleton instance
  static Websocket_manager *getInstance(const char *ssid, const char *password,
                                        const char *url,
                                        const uint16_t port,
                                        const char *mqtt_server, const uint16_t mqtt_port,
                                        const char *mqtt_user, const char *mqtt_password,
                                        const uint8_t pin_DHT22)
  {
    static Websocket_manager instance_(ssid, password, url, port, mqtt_server, mqtt_port,
                                       mqtt_user, mqtt_password,
                                       pin_DHT22); // Use static local variable for thread-safe singleton
    instance = &instance_;
    return instance;
  }

  // Clean up disconnected WebSocket clients
  void cleanupClients()
  {
    // Clean up disconnected clients
    ws.cleanupClients();
  }

  // Read CH2O data
  void read_ch2o()
  {
    // For debugging
    const std::pair<bool, const std::pair<uint16_t, float>> res = ze08->read();
    if (res.first)
    {
      Serial.printf("CH2O: %d ppb, %.2f mg/m3\n", res.second.first, res.second.second);
    }
    else
    {
      Serial.println("CH2O: read failed");
    }
    delay(1000);
  }

  // Disconnect all WebSocket clients
  void disconnectAllClients()
  {
    ws.closeAll();
    // Give clients some time to handle disconnection
    delay(100);
  }

  // Push sensor data to MQTT
  void mqtt_push()
  {
    if (delayer_mqtt_push.is_expired_when_delay(7000))
    {
      mqtt_push_imple();
    }
  }

  // 检查WiFi连接状态
  bool isWiFiConnected()
  {
    return WiFi.status() == WL_CONNECTED;
  }

  // 重新连接WiFi
  bool reconnectWiFi()
  {
    if (isWiFiConnected())
      return true;

    Serial.println("WiFi disconnected, attempting to reconnect...");
    WiFi.disconnect();
    delay(1000);
    WiFi.begin(this->ssid, this->password);

    unsigned long startAttemptTime = millis();
    // 等待WiFi连接，超时时间30秒
    while (WiFi.status() != WL_CONNECTED && (millis() - startAttemptTime) < 30000)
    {
      delay(500);
      Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED)
    {
      Serial.println("\nWiFi reconnected successfully");
      Serial.print("Got IP: ");
      Serial.println(WiFi.localIP());
      return true;
    }
    else
    {
      Serial.println("\nWiFi reconnect failed");
      return false;
    }
  }

private:
  // Private constructor
  explicit Websocket_manager(const char *ssid, const char *password,
                             const char *url, const uint16_t port,
                             const char *mqtt_server, const uint16_t mqtt_port,
                             const char *mqtt_user, const char *mqtt_password,
                             const uint8_t pin_DHT22)
      : ssid(ssid), password(password), url(url), port(port),
        server(port), ws(url),
        mqtt_server(mqtt_server), mqtt_port(mqtt_port),
        mqtt_user(mqtt_user), mqtt_password(mqtt_password),
        espClient(), client(espClient), delayer_mqtt_push(),
        dht22(Sensor_DHT22::getInstance(pin_DHT22)),
        ze08(Sensor_ZE08_CH2O::getInstance(true))
  {
    client.setServer(mqtt_server, mqtt_port);
    setup();
  }

  // Disable copy constructor and assignment operator
  Websocket_manager(const Websocket_manager &) = delete;
  Websocket_manager &operator=(const Websocket_manager &) = delete;

  ~Websocket_manager()
  {
    // Ensure all connections are disconnected before destruction
    disconnectAllClients();
    server.end();
  }

  // Implement MQTT data push
  void mqtt_push_imple()
  {
    // 先检查WiFi连接
    if (!reconnectWiFi())
    {
      Serial.println("Cannot push data to MQTT, WiFi not connected");
      return;
    }

    if (!client.connected())
    {
      if (!connect_mqtt())
      {
        return;
      }
    }
    client.loop();

    // Read DHT22 data
    std::pair<float, float> tem_hum = dht22->get_temperature_humidity();
    if (!isnan(tem_hum.first))
    { // Publish only when data is valid
      char tem_str[8];
      dtostrf(tem_hum.first, 1, 2, tem_str);
#ifdef DEBUG_MODE
      Serial.printf("Temperature: %s°C\n", tem_str);
#endif
      client.publish("homeassistant/sensor/dht22/temperature", tem_str);
    }
    if (!isnan(tem_hum.second))
    {
      char hum_str[8];
      dtostrf(tem_hum.second, 1, 2, hum_str);
#ifdef DEBUG_MODE
      Serial.printf("Humidity: %s%%\n", hum_str);
#endif
      client.publish("homeassistant/sensor/dht22/humidity", hum_str);
    }
    const std::pair<bool, const std::pair<uint16_t, float>> ch2o = ze08->read();
    if (ch2o.first)
    {
      char ch2o_str[10];
      dtostrf(ch2o.second.second, 1, 5, ch2o_str); // Keep 5 decimal places
#ifdef DEBUG_MODE
      Serial.printf("CH2O: %s mg/m³\n", ch2o_str);
#endif
      client.publish("homeassistant/sensor/ze08_ch2o/state", ch2o_str);
    }
  }

  void publish_mqtt_discovery()
  {
#ifdef DEBUG_MODE
    Serial.println("Publishing MQTT discovery messages");
#endif

    client.publish("homeassistant/sensor/dht22_temperature/config",
                   "{\"name\":\"DHT22 Temperature\",\"unique_id\":\"dht22_temp_001\",\"state_topic\":\"homeassistant/sensor/dht22/temperature\",\"unit_of_measurement\":\"°C\",\"device_class\":\"temperature\",\"state_class\":\"measurement\"}", true);
    client.publish("homeassistant/sensor/dht22_humidity/config",
                   "{\"name\":\"DHT22 Humidity\",\"unique_id\":\"dht22_hum_001\",\"state_topic\":\"homeassistant/sensor/dht22/humidity\",\"unit_of_measurement\":\"%\",\"device_class\":\"humidity\",\"state_class\":\"measurement\"}", true);
    client.publish("homeassistant/sensor/ze08_ch2o/config",
                   "{\"name\":\"ZE08 CH2O\",\"unique_id\":\"ze08_ch2o_001\",\"state_topic\":\"homeassistant/sensor/ze08_ch2o/state\",\"unit_of_measurement\":\"mg/m³\",\"device_class\":\"volatile_organic_compounds\",\"state_class\":\"measurement\"}", true);
  }

  // Connect to MQTT server
  bool connect_mqtt()
  {
    if (client.connected())
    {
#ifdef DEBUG_MODE
      Serial.println("MQTT client already connected");
#endif
      return true;
    }

    // 确保WiFi已连接
    if (!isWiFiConnected())
    {
      Serial.println("Cannot connect to MQTT, WiFi not connected");
      return false;
    }

#ifdef DEBUG_MODE
    Serial.print("Attempting to connect to MQTT server: ");
    Serial.println(mqtt_server);
    Serial.print("MQTT Port: ");
    Serial.println(mqtt_port);
    Serial.print("MQTT User: ");
    Serial.println(mqtt_user);
#endif

    // 尝试连接MQTT服务器
    if (client.connect("ESP32Client", mqtt_user, mqtt_password))
    {
#ifdef DEBUG_MODE
      Serial.println("MQTT connection successful");
#endif
      publish_mqtt_discovery();
      return true;
    }
    else
    {
      Serial.print("MQTT connection failed, error code= ");
      Serial.println(client.state());

      // 根据错误代码提供更详细的信息
      int state = client.state();
      switch (state)
      {
      case -4:
        Serial.println("MQTT_CONNECTION_TIMEOUT - the server didn't respond within the keepalive time");
        break;
      case -3:
        Serial.println("MQTT_CONNECTION_LOST - the network connection was broken");
        break;
      case -2:
        Serial.println("MQTT_CONNECT_FAILED - the network connection failed");
        break;
      case -1:
        Serial.println("MQTT_DISCONNECTED - the client is disconnected cleanly");
        break;
      case 0:
        Serial.println("MQTT_CONNECTED - the client is connected");
        break;
      case 1:
        Serial.println("MQTT_CONNECT_BAD_PROTOCOL - the server doesn't support the requested version of MQTT");
        break;
      case 2:
        Serial.println("MQTT_CONNECT_BAD_CLIENT_ID - the server rejected the client identifier");
        break;
      case 3:
        Serial.println("MQTT_CONNECT_UNAVAILABLE - the server was unavailable");
        break;
      case 4:
        Serial.println("MQTT_CONNECT_BAD_CREDENTIALS - the username/password were rejected");
        break;
      case 5:
        Serial.println("MQTT_CONNECT_UNAUTHORIZED - the client was not authorized to connect");
        break;
      default:
        Serial.println("Unknown MQTT error code");
        break;
      }

      return false;
    }
  }

  // Initialize Wi-Fi, WebSocket, and MQTT
  void setup()
  {
    // Initialize serial port only once
    if (!Serial)
    {
      Serial.begin(115200);
    }

#ifdef DEBUG_MODE
    Serial.print("Connecting to ");
    Serial.println(ssid);
#endif

    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED)
    {
      delay(500);
#ifdef DEBUG_MODE
      Serial.print(".");
#endif
    }

#ifdef DEBUG_MODE
    Serial.println("");
    Serial.println("Connected..!");
    Serial.print("Got IP: ");
    Serial.println(WiFi.localIP());
#endif

    ws.onEvent(event_handler_static);
    server.addHandler(&ws);
    server.begin();
    connect_mqtt();
  }

  // Handle WebSocket messages
  static void handle_websocket_message(AsyncWebSocket *server, AsyncWebSocketClient *client, void *arg, uint8_t *data, size_t len)
  {

    // Check if instance and client exist
    if (!instance || !client)
      return;

    // Check if client is ready to send data
    if (!client->canSend())
    {
#ifdef DEBUG_MODE
      Serial.printf("Client #%u is not ready to send data\n", client->id());
#endif
      return;
    }

    AwsFrameInfo *info = (AwsFrameInfo *)arg;
    if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT)
    {
      // Ensure the string has a null terminator
      if (len < 512)
      {
        data[len] = 0;
      }
      else
      {
        data[512] = 0;
      }
      // Replace DynamicJsonDocument with JsonDocument
      JsonDocument doc;
      DeserializationError error = deserializeJson(doc, data);

      if (error)
      {
#ifdef DEBUG_MODE
        Serial.print("JSON parsing failed: ");
        Serial.println(error.c_str());
#endif
        return;
      }

      const char *from = doc["from"] | "";
      if (strcmp(from, "AI_server") == 0)
      {
        const char *type = doc["type"] | "";
        if (strcmp(type, "humidity_temperature") == 0)
        {
          std::pair<float, float> th = instance->dht22->get_temperature_humidity();
          // Replace DynamicJsonDocument with JsonDocument
          JsonDocument doc_resp;
          doc_resp["from"] = "esp32_sensors";
          doc_resp["to"] = "AI_server";
          doc_resp["id"] = doc["id"];
          doc_resp["type"] = "humidity_temperature";
          doc_resp["temperature"] = th.first;
          doc_resp["humidity"] = th.second;

          std::string output;
          output.reserve(512);
          serializeJson(doc_resp, output);
          instance->ws.text(client->id(), output.c_str());
        }
        else if (strcmp(type, "ch2o") == 0)
        {
          // Handle formaldehyde concentration query
          const std::pair<bool, const std::pair<uint16_t, float>> res = instance->ze08->read();
          // Replace DynamicJsonDocument with JsonDocument
          JsonDocument doc_resp;
          doc_resp["from"] = "esp32_sensors";
          doc_resp["to"] = "AI_server";
          doc_resp["id"] = doc["id"];
          doc_resp["type"] = "ch2o";
          doc_resp["success"] = res.first;
          doc_resp["ppb"] = res.second.first;
          doc_resp["mgm3"] = res.second.second;

          std::string output;
          output.reserve(512);
          serializeJson(doc_resp, output);
          instance->ws.text(client->id(), output.c_str());
        }
      }
    }
  }

  // WebSocket event handler
  static void event_handler_static(AsyncWebSocket *server, AsyncWebSocketClient *client,
                                   AwsEventType type, void *arg, uint8_t *data, size_t len)
  {
    if (!client)
      return;

    switch (type)
    {
    case WS_EVT_CONNECT:
#ifdef DEBUG_MODE
      Serial.printf("WebSocket client #%u connected from %s\n", client->id(), client->remoteIP().toString().c_str());
#endif
      break;

    case WS_EVT_DISCONNECT:
#ifdef DEBUG_MODE
      Serial.printf("WebSocket client #%u disconnected\n", client->id());
#endif
      // Cleanup operations can be added here after client disconnection
      break;

    case WS_EVT_DATA:
      handle_websocket_message(server, client, arg, data, len);
      break;

    case WS_EVT_PONG:
#ifdef DEBUG_MODE
      Serial.printf("WebSocket client #%u pong received\n", client->id());
#endif
      break;

    case WS_EVT_ERROR:
#ifdef DEBUG_MODE
      Serial.printf("WebSocket client #%u error: %s\n", client->id(), (char *)data);
#endif
      // Actively disconnect the client when an error occurs
      if (client->canSend())
      {
        client->close();
      }
      break;
    }
  }

  const char *ssid;
  const char *password;
  const char *url;
  uint16_t port;
  const char *mqtt_server;
  uint16_t mqtt_port;
  const char *mqtt_user;
  const char *mqtt_password;
  WiFiClient espClient;
  PubSubClient client;
  AsyncWebServer server;
  AsyncWebSocket ws;
  Sensor_DHT22 *dht22;
  Sensor_ZE08_CH2O *ze08;
  NonblockingDelayer delayer_mqtt_push;
  static Websocket_manager *instance;
};

Websocket_manager *Websocket_manager::instance = nullptr;

Websocket_manager *websocket_manager;
// Example usage
uint8_t Sensor_HC_SR501_pin = 26;
bool led_state = 0;
const uint8_t led_pin = 2;
unsigned long lastRestartTime = 0;
const unsigned long RESTART_INTERVAL = 24 * 60 * 60 * 1000; // 24小时，单位毫秒

void restartESP32()
{
  Serial.println("Restarting ESP32 after 24 hours...");
  delay(1000); // 给串口打印时间
  ESP.restart();
}

void setup()
{
  // 初始化看门狗
  esp_task_wdt_init(WDT_TIMEOUT, true); // 启用中断并在超时后重置系统
  esp_task_wdt_add(NULL);               // 将当前任务添加到看门狗监控

  pinMode(led_pin, OUTPUT);
  pinMode(Sensor_HC_SR501_pin, INPUT);
  digitalWrite(led_pin, LOW);

  const char *ssid = "403";
  const char *password = "14031403";
  const char *mqtt_server = "192.168.10.236";
  const uint16_t mqtt_port = 1883;
  const char *mqtt_user = "mosquitto";
  const char *mqtt_password = "mosquitto_mqtt";

#ifdef DEBUG_MODE
  Serial.begin(115200);
  Serial.println("Starting ESP32 Sensor Node...");
#endif

  // 初始化重启计时器
  lastRestartTime = millis();

  // Create singleton instance
  websocket_manager = Websocket_manager::getInstance(ssid, password, "/ws", 80,
                                                     mqtt_server, mqtt_port,
                                                     mqtt_user, mqtt_password, 4);
}

// Called at the end of the program
void end()
{
  // Ensure the instance is safely destroyed
  if (websocket_manager)
  {
    // No need to call destroyInstance as singleton is managed by static local variable
    websocket_manager = nullptr;
  }
}

void loop()
{
  // 喂狗，重置看门狗计时器
  esp_task_wdt_reset();

  // Regularly clean up disconnected clients
  websocket_manager->cleanupClients();
  websocket_manager->mqtt_push();

  // 检查WiFi连接状态
  if (!websocket_manager->isWiFiConnected())
  {
    Serial.println("WiFi disconnected in loop, attempting to reconnect...");
    // 尝试重新连接WiFi
    if (!websocket_manager->reconnectWiFi())
    {
      // 如果重新连接失败，添加一些延迟避免CPU占用过高
      delay(5000);
    }
  }

  // 检查是否需要重启ESP32 (每24小时)
  unsigned long currentMillis = millis();
  if (currentMillis - lastRestartTime >= RESTART_INTERVAL)
  {
    restartESP32();
  }

  // Add some non-blocking delay to allow the system time to handle other tasks
  delay(10);
}