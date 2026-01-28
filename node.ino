#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <WiFiManager.h>
#include <ESP8266mDNS.h> // <--- LIBRERÍA NUEVA IMPORTANTE

// --- CONFIGURACIÓN ---
const int RELAY_PIN = 5; // D1
const char* SECRET_TOKEN = "istae1805A"; 
const char* HOSTNAME = "puerta-tesis"; // <--- ESTE SERÁ SU NOMBRE EN LA RED

ESP8266WebServer server(80);

// Variables para el temporizador (millis)
bool releActivo = false;
unsigned long tiempoInicio = 0;
const long duracionApertura = 2000;

void setup() {
  Serial.begin(115200);
  
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW); // Inicia apagado

  WiFiManager wifiManager;
  // ELIMINAMOS LAS LÍNEAS DE setSTAStaticIPConfig
  // Ahora dejamos que el router decida la IP automáticamente (DHCP)

  // Si no conecta, crea la red "CONFIG_PUERTA"
  if (!wifiManager.autoConnect("CONFIG_PUERTA", "12345678")) {
    delay(3000);
    ESP.reset();
  }

  Serial.println("");
  Serial.print("✅ Conectado! IP Dinámica: ");
  Serial.println(WiFi.localIP());

  // --- INICIAR mDNS (LA MAGIA) ---
  if (MDNS.begin(HOSTNAME)) {
    Serial.println("✅ mDNS iniciado. Ahora soy accesible como: puerta-tesis.local");
  } else {
    Serial.println("Error configurando mDNS");
  }

  // Rutas
  server.on("/", []() {
    server.send(200, "text/plain", "Sistema Puerta ONLINE (Modo mDNS)");
  });

  server.on("/api/abrir", []() {
    if (server.hasArg("token") && server.arg("token") == SECRET_TOKEN) {
      server.send(200, "text/plain", "OK_ABRIENDO");
      activarLogica();
    } else {
      server.send(403, "text/plain", "ERROR_TOKEN");
    }
  });

  server.begin();
}

void loop() {
  server.handleClient();
  MDNS.update(); // <--- Mantiene el nombre visible en la red

  // Lógica no bloqueante
  if (releActivo) {
    if (millis() - tiempoInicio >= duracionApertura) {
      digitalWrite(RELAY_PIN, LOW);
      releActivo = false;
      Serial.println("🔒 Puerta cerrada");
    }
  }
}

void activarLogica() {
  digitalWrite(RELAY_PIN, HIGH);
  releActivo = true;
  tiempoInicio = millis();
  Serial.println("🔓 Abriendo puerta...");
}