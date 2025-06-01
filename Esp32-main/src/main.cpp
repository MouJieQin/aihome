#include <DHT.h>
#include <WiFi.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <utility>
#include "WZ.h"

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
    if (instance == nullptr)
    {
      instance = new Sensor_ZE08_CH2O(activeMode);
    }
    return instance;
  }

  // Destroy singleton instance
  static void destroyInstance()
  {
    delete instance;
    instance = nullptr;
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
  // Request sensor data
  void requestRead()
  {
    wz.requestRead();
  }

private:
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

private:
  WZ wz;
  WZ::DATA hcho_data;
  bool is_active_mode;
  static Sensor_ZE08_CH2O *instance;
};

Sensor_ZE08_CH2O *Sensor_ZE08_CH2O::instance = nullptr;

// Sensor class for DHT22 sensor
class Sensor_DHT22
{
public:
  // Get singleton instance
  static Sensor_DHT22 *getInstance(const uint8_t pin)
  {
    if (instance == nullptr)
    {
      instance = new Sensor_DHT22(pin);
      instance->setup();
    }
    return instance;
  }

  // Destroy singleton instance
  static void destroyInstance()
  {
    delete instance;
    instance = nullptr;
  }

  // Read humidity
  const float readHumidity()
  {
    // 减少延时，避免阻塞系统
    delay(20);
    return dht.readHumidity();
  }

  // Read temperature
  const float readTemperature()
  {
    // 减少延时，避免阻塞系统
    delay(20);
    return dht.readTemperature();
  }

  // Get temperature and humidity
  const std::pair<float, float> get_temperature_humidity()
  {
    // 减少延时，避免阻塞系统
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
  ~Sensor_DHT22()
  {
  }

private:
  // Initialize sensor
  void setup()
  {
    // 只初始化一次串口
    if (!Serial)
    {
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

class NonblockingDelayer
{
public:
  explicit NonblockingDelayer() : lastUpdate(ULONG_MAX) {}
  ~NonblockingDelayer()
  {
  }
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

private:
  unsigned long lastUpdate;
};

// Class to manage WebSocket and MQTT communication
class Websocket_manager
{
public:
  // Clean up disconnected WebSocket clients
  void cleanupClients()
  {
    // 清理断开的客户端
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

  // Get singleton instance
  static Websocket_manager *getInstance(const String &ssid, const String &password,
                                        const String &url,
                                        const uint16_t port,
                                        const String &mqtt_server, const uint16_t mqtt_port,
                                        const String &mqtt_user, const String &mqtt_password,
                                        const uint8_t pin_DHT22)
  {
    if (instance == nullptr)
    {
      instance = new Websocket_manager(ssid, password, url, port, mqtt_server, mqtt_port,
                                       mqtt_user, mqtt_password,
                                       pin_DHT22);
      instance->setup();
    }
    return instance;
  }

  // Destroy singleton instance
  static void destroyInstance()
  {
    if (instance)
    {
      instance->disconnectAllClients();
      instance->dht22->destroyInstance();
      instance->ze08->destroyInstance();
      delete instance;
      instance = nullptr;
    }
  }

  // Disconnect all WebSocket clients
  void disconnectAllClients()
  {
    ws.closeAll();
    // 给客户端一些时间处理断开
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

private:
  // Private constructor
  explicit Websocket_manager(const String &ssid, const String &password,
                             const String &url, const uint16_t port,
                             const String &mqtt_server, const uint16_t mqtt_port,
                             const String &mqtt_user, const String &mqtt_password,
                             const uint8_t pin_DHT22)
      : ssid(ssid), password(password), url(url), port(port),
        server(port), ws(url),
        mqtt_server(mqtt_server), mqtt_port(mqtt_port),
        mqtt_user(mqtt_user), mqtt_password(mqtt_password),
        espClient(), client(espClient), delayer_mqtt_push(),
        dht22(nullptr), ze08(nullptr)
  {
    client.setServer(mqtt_server.c_str(), mqtt_port);
    dht22 = Sensor_DHT22::getInstance(pin_DHT22);
    ze08 = Sensor_ZE08_CH2O::getInstance(true);
  }

  // Disable copy constructor and assignment operator
  Websocket_manager(const Websocket_manager &) = delete;
  Websocket_manager &operator=(const Websocket_manager &) = delete;

  ~Websocket_manager()
  {
    // 确保在销毁前断开所有连接
    disconnectAllClients();
    server.end();
  }

  // Implement MQTT data push
  void mqtt_push_imple()
  {
    if (!client.connected())
    {
      if (!connect_mqtt())
      {
        return;
      }
    }
    client.loop();

    // 读取DHT22数据
    std::pair<float, float> tem_hum = instance->dht22->get_temperature_humidity();
    if (!isnan(tem_hum.first))
    { // 仅在数据有效时发布
      char tem_str[8];
      dtostrf(tem_hum.first, 1, 2, tem_str);
      Serial.printf("Temperature: %s°C\n", tem_str);
      client.publish("homeassistant/sensor/dht22/temperature", tem_str);
    }
    if (!isnan(tem_hum.second))
    {
      char hum_str[8];
      dtostrf(tem_hum.second, 1, 2, hum_str);
      Serial.printf("Humidity: %s%%\n", hum_str);
      client.publish("homeassistant/sensor/dht22/humidity", hum_str);
    }
    const std::pair<bool, const std::pair<uint16_t, float>> ch2o = instance->ze08->read();
    if (ch2o.first)
    {
      char ch2o_str[10];
      dtostrf(ch2o.second.second, 1, 5, ch2o_str); // 保留5位小数
      Serial.printf("CH2O: %s mg/m³\n", ch2o_str);
      client.publish("homeassistant/sensor/ze08_ch2o/state", ch2o_str);
    }
  }

  void publish_mqtt_discovery()
  {
    client.publish("homeassistant/sensor/dht22_temperature/config",
                   "{\"name\":\"DHT22 Temperature\",\"unique_id\":\"dht22_temp_001\",\"state_topic\":\"homeassistant/sensor/dht22/temperature\",\"unit_of_measurement\":\"°C\",\"device_class\":\"temperature\"}", true);
    client.publish("homeassistant/sensor/dht22_humidity/config",
                   "{\"name\":\"DHT22 Humidity\",\"unique_id\":\"dht22_hum_001\",\"state_topic\":\"homeassistant/sensor/dht22/humidity\",\"unit_of_measurement\":\"%\",\"device_class\":\"humidity\"}", true);
    client.publish("homeassistant/sensor/ze08_ch2o/config",
                   "{\"name\":\"ZE08 CH2O\",\"unique_id\":\"ze08_ch2o_001\",\"state_topic\":\"homeassistant/sensor/ze08_ch2o/state\",\"unit_of_measurement\":\"mg/m³\",\"device_class\":\"volatile_organic_compounds\"}", true);
  }

  // Connect to MQTT server
  bool connect_mqtt()
  {
    if (client.connected())
    {
      return true;
    }
    Serial.println("尝试连接MQTT服务器...");
    if (client.connect("ESP32Client", mqtt_user.c_str(), mqtt_password.c_str()))
    {
      Serial.println("MQTT连接成功");
      publish_mqtt_discovery();
      return true;
    }
    else
    {
      Serial.print("MQTT连接失败，错误码= ");
      Serial.println(client.state());
      return false;
    }
    return false;
  }

  // Initialize Wi-Fi, WebSocket, and MQTT
  void setup()
  {
    // 只初始化一次串口
    if (!Serial)
    {
      Serial.begin(115200);
    }

    Serial.print("Connecting to ");
    Serial.println(ssid);

    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED)
    {
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
    connect_mqtt();
  }

  // Handle WebSocket messages
  static void handle_websocket_message(AsyncWebSocket *server, AsyncWebSocketClient *client, void *arg, uint8_t *data, size_t len)
  {
    // 检查实例是否存在
    if (instance == nullptr || client == nullptr)
      return;

    // 检查客户端是否有效
    if (!client->canSend())
    {
      Serial.printf("Client #%u is not ready to send data\n", client->id());
      return;
    }

    AwsFrameInfo *info = (AwsFrameInfo *)arg;
    if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT)
    {
      // 确保字符串有终止符
      data[len] = 0;
      DynamicJsonDocument doc(512);
      DeserializationError error = deserializeJson(doc, data);

      if (error)
      {
        Serial.print("JSON parsing failed: ");
        Serial.println(error.c_str());
        return;
      }

      const char *from = doc["from"] | "";
      if (strcmp(from, "AI_server") == 0)
      {
        const char *type = doc["type"] | "";
        if (strcmp(type, "humidity_temperature") == 0)
        {
          std::pair<float, float> th = instance->dht22->get_temperature_humidity();
          DynamicJsonDocument doc_resp(512);
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
          // 处理甲醛浓度查询
          const std::pair<bool, const std::pair<uint16_t, float>> res = instance->ze08->read();
          DynamicJsonDocument doc_resp(512);
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
    if (client == nullptr)
      return;

    switch (type)
    {
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
      if (client->canSend())
      {
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
  String mqtt_server;
  uint16_t mqtt_port;
  String mqtt_user;
  String mqtt_password;
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
// 示例使用方法
uint8_t Sensor_HC_SR501_pin = 26;
bool led_state = 0;
const uint8_t led_pin = 2;

void setup()
{
  pinMode(led_pin, OUTPUT);
  pinMode(Sensor_HC_SR501_pin, INPUT);
  digitalWrite(led_pin, LOW);

  const char *ssid = "403";
  const char *password = "14031403";
  const char *mqtt_server = "192.168.10.236";
  const uint16_t mqtt_port = 1883;
  const char *mqtt_user = "mosquitto";
  const char *mqtt_password = "mosquitto_mqtt";

  // 创建单例实例
  websocket_manager = Websocket_manager::getInstance(ssid, password, "/ws", 80,
                                                     mqtt_server, mqtt_port,
                                                     mqtt_user, mqtt_password, 4);
}

// 在程序结束时调用
void end()
{
  // 确保安全销毁实例
  if (websocket_manager)
  {
    Websocket_manager::destroyInstance();
    websocket_manager = nullptr;
  }
}

void loop()
{
  // 定期清理断开的客户端
  websocket_manager->cleanupClients();
  websocket_manager->mqtt_push();
  // 添加一些非阻塞延时，让系统有时间处理其他任务
  delay(10);
}