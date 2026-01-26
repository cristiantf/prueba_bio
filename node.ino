#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <WiFiManager.h> 

// --- CONFIGURACIÓN ---
const int RELAY_PIN = 5;      // Pin D1 en NodeMCU
const int LED_PIN = 2;        // Pin del LED integrado en NodeMCU
const char* SECRET_TOKEN = "istae1805A"; // Token de seguridad

// --- VARIABLES PARA TEMPORIZADOR NO BLOQUEANTE ---
bool releActivo = false;
unsigned long tiempoInicioRele = 0;
const long duracionApertura = 3000; // 3 segundos

// --- VARIABLES PARA HEARTBEAT LED ---
unsigned long tiempoAnteriorLed = 0;
int estadoLed = LOW;

// --- IP FIJA ---
IPAddress staticIP(192, 168, 1, 19);
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress dns(8, 8, 8, 8); // DNS de Google

ESP8266WebServer server(80);

void setup() {
  Serial.begin(115200);
  Serial.println(F("\n--- INICIANDO SISTEMA DE PUERTA v2 ---"));

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH); 
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);

  WiFiManager wifiManager;
  wifiManager.setSTAStaticIPConfig(staticIP, gateway, subnet, dns);
  
  Serial.println(F("Conectando a WiFi..."));
  if (!wifiManager.autoConnect("PUERTA_TESIS_AP", "12345678")) {
    Serial.println(F("Fallo al conectar. Reiniciando..."));
    delay(3000);
    ESP.reset();
  }

  Serial.println(F("\n¡Conexión WiFi exitosa!"));
  Serial.print(F("IP Asignada: "));
  Serial.println(WiFi.localIP());

  // --- RUTAS DEL SERVIDOR WEB ---
  server.on("/", handleRoot);
  server.on("/api/abrir", handleAbrir); 
  
  // Manejador para rutas no encontradas (404)
  server.onNotFound(handleNotFound);

  server.begin();
  Serial.println(F("Servidor HTTP iniciado."));
}

void loop() {
  server.handleClient();

  if (releActivo && (millis() - tiempoInicioRele >= duracionApertura)) {
    digitalWrite(RELAY_PIN, HIGH);
    releActivo = false;
    Serial.println(F("LOG: Relé desactivado automáticamente."));
  }
  
  if (millis() - tiempoAnteriorLed >= 1000) {
    tiempoAnteriorLed = millis();
    digitalWrite(LED_PIN, estadoLed);
    estadoLed = (estadoLed == LOW) ? HIGH : LOW;
  }
}

// --- MANEJADORES DE RUTAS ---

void handleRoot() {
  char temp[100]; // Buffer para formatear texto
  
  // Envía la cabecera
  server.sendHeader("Content-Type", "text/html");
  server.send(200, "text/plain", ""); // Envía el código 200 y empieza el cuerpo

  // Envía el contenido por partes para no usar el objeto String
  server.sendContent(F("<!DOCTYPE html><html><head><title>Estado del Sistema</title></head><body>"));
  server.sendContent(F("<h1>Sistema de Puerta Online</h1>"));
  server.sendContent(F("<p><strong>Estado:</strong> Activo</p>"));
  
  snprintf(temp, sizeof(temp), "<p><strong>IP:</strong> %s</p>", WiFi.localIP().toString().c_str());
  server.sendContent(temp);

  snprintf(temp, sizeof(temp), "<p><strong>Memoria Libre (Heap):</strong> %d bytes</p>", ESP.getFreeHeap());
  server.sendContent(temp);

  snprintf(temp, sizeof(temp), "<p><strong>Tiempo Activo:</strong> %lu segundos</p>", millis() / 1000);
  server.sendContent(temp);

  server.sendContent("</body></html>");
  server.sendContent(""); // Finaliza la respuesta
}

void handleAbrir() {
  Serial.println(F("\nLOG: Petición recibida en /api/abrir"));
  if (!server.hasArg("token") || server.arg("token") != SECRET_TOKEN) {
    Serial.println(F("ERROR: Token no válido o ausente."));
    server.send(403, "text/plain", "ERROR_TOKEN_INVALIDO");
    return;
  }

  Serial.println(F("OK: Token válido. Activando relé."));
  server.send(200, "text/plain", "OK_ABRIENDO_PUERTA");
  
  digitalWrite(RELAY_PIN, LOW);
  releActivo = true;
  tiempoInicioRele = millis();
}

void handleNotFound(){
  String uri = server.uri();
  Serial.print(F("ERROR 404: Ruta no encontrada: "));
  Serial.println(uri);
  server.send(404, "text/plain", "404: Not Found\nURI: " + uri);
}